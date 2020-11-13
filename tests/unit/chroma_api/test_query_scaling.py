from collections import namedtuple

from django.db import connection
from django.test.utils import CaptureQueriesContext

from chroma_api.filesystem import FilesystemResource
from chroma_api.host import HostResource
from chroma_api.target import TargetResource
from chroma_api.volume import VolumeResource
from chroma_core.lib.cache import ObjectCache
from chroma_core.models import (
    LogMessage,
    ManagedHost,
    LNetConfiguration,
    VolumeNode,
    Volume,
    ManagedFilesystem,
    ManagedTarget,
    ManagedTargetMount,
    ManagedMgs,
    ManagedMdt,
    ManagedOst,
    CorosyncConfiguration,
)
from tests.unit.chroma_api.chroma_api_test_case import ChromaApiTestCase
from tests.unit.chroma_core.helpers import fake_log_message, synthetic_volume


Order1 = namedtuple("Order1", ["query_count"])
OrderN = namedtuple("OrderN", ["queries_per_object"])
OrderBad = namedtuple("OrderBad", [])


# These are tripwires: if you change the chroma_api behaviour such
# that query counts change, these tests start failing.  If the query
# count goes down, yay, update this number downwards.  If it goes up
# then think about whether you meant to do that, and grudgingly
# update this number upwards if necessary, or go back and
# revise the API change.
QUERIES_PER_TARGET = 3  # queries per target accessing that resource directly
QUERIES_PER_FILESYSTEM_TARGET = 4  # queries per target when included in a filesystem resource
QUERIES_PER_VOLUME = 1  # queries per volume object when reading volumes
QUERIES_PER_VOLUME_HOST = 1  # additional queries per-volume per-host
QUERIES_TOTAL_UNDECORATED_LOGS = 5  # total queries to get all log messages (when they don't have any NIDs or targets)
PAGING_AND_AUTH_QUERIES = 5


class TestQueryScaling(ChromaApiTestCase):
    """
    Given a function for creating N objects, a function for querying N
    objects, and a means of counting DB queries, determine
    the scaling of the number of DB queries with respect to the number
    of objects in a collection.

    The ideal is O(1) (i.e. running a single SELECT for all the objects).
    """

    def setUp(self):
        super(TestQueryScaling, self).setUp()

        # Reset storage_plugin_manager (needed because of the DB rollback between tests
        # getting its record of resource classes out of sync with the DB)
        import chroma_core.lib.storage_plugin.manager

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = (
            chroma_core.lib.storage_plugin.manager.StoragePluginManager()
        )

    def tearDown(self):
        super(TestQueryScaling, self).tearDown()

    def _measure_scaling(self, create_n, measured_resource, scaled_resource=None):
        """

        :param create_n: Function to create N of scaled_resource
        :param measured_resource: The resource we will measure the query load for
        :param scaled_resource: The object which is actually being scaled with N
        :return: Instance of Order1, OrderN, OrderBad
        """
        if scaled_resource is None:
            scaled_resource = measured_resource

        query_counts = {}
        samples = [5, 6, 7, 8]

        for n in samples:
            ObjectCache.clear()
            create_n(n)
            # Queries get reset at the start of a request
            self.assertEqual(scaled_resource._meta.queryset.count(), n)
            with CaptureQueriesContext(connection) as queries:
                response = self.api_client.get("/api/%s/" % measured_resource._meta.resource_name, data={"limit": 0})
                self.assertEqual(
                    response.status_code, 200, "%s:%s" % (response.content, measured_resource._meta.resource_name)
                )
                query_count = len(queries)

            self.assertEqual(len(self.deserialize(response)["objects"]), measured_resource._meta.queryset.count())
            query_counts[n] = query_count

        # Ignore samples[0], it was just to clear out any setup overhead from first call to API

        # gradient between samples[1] and samples[2]
        grad1 = (query_counts[samples[2]] - query_counts[samples[1]]) / (samples[2] - samples[1])
        # gradient between samples[2] and samples[3]
        grad2 = (query_counts[samples[3]] - query_counts[samples[2]]) / (samples[3] - samples[2])

        if grad1 == 0 and grad2 == 0:
            # Hoorah, O(1)
            return Order1(query_counts[samples[3]])
        elif grad1 > 0 and grad1 == grad2:
            # O(N)
            return OrderN(grad1)
        else:
            # Worse than O(N)
            return OrderBad()

    def _create_n_hosts(self, n):
        LNetConfiguration.objects.all().delete()
        ManagedHost.objects.update(not_deleted=None)

        for i in range(0, n):
            hostname = "fakehost_%.3d" % i

            host = ManagedHost.objects.create(fqdn=hostname, nodename=hostname, address=hostname)
            LNetConfiguration.objects.get_or_create(host=host)
            CorosyncConfiguration.objects.get_or_create(host=host)

    def _create_san_volumes(self, n_servers, n_volumes):
        """SAN-like volume configuration with each volume connected to all servers"""
        self._create_n_hosts(n_servers)
        VolumeNode.objects.update(not_deleted=None)
        Volume.objects.update(not_deleted=None)

        for i in range(0, n_volumes):
            volume = synthetic_volume()
            path = "/dev/volume_%s" % volume.id
            for i, host in enumerate(ManagedHost.objects.all()):
                primary = i == 0
                VolumeNode.objects.create(volume=volume, host=host, path=path, primary=primary)

    def _create_n_volumes_host_pairs(self, n_volumes):
        """SCSI-like volume configuration with each volume connected to two servers"""
        self._create_n_hosts(n_volumes / 2)
        VolumeNode.objects.update(not_deleted=None)
        Volume.objects.update(not_deleted=None)

        for i in range(0, n_volumes):
            volume = synthetic_volume()
            host_1 = ManagedHost.objects.get(fqdn="fakehost_%.3d" % ((i / 2) % (n_volumes / 2)))
            host_2 = ManagedHost.objects.get(fqdn="fakehost_%.3d" % ((i / 2 + 1) % (n_volumes / 2)))
            assert host_1 != host_2
            path = "/dev/volume_%s" % volume.id
            VolumeNode.objects.create(volume=volume, host=host_1, path=path, primary=True)
            VolumeNode.objects.create(volume=volume, host=host_2, path=path, primary=False)

    def test_volumes(self):
        # Creating N volumes with a fixed number of volumes visible to each host
        host_pairs_scaling = self._measure_scaling(self._create_n_volumes_host_pairs, VolumeResource)
        self.assertIsInstance(host_pairs_scaling, OrderN)
        self.assertEqual(host_pairs_scaling.queries_per_object, QUERIES_PER_VOLUME)

        # Creating N volumes with all volumes visible to a fixed number of hosts
        fixed_host_count = 8

        def create_n_volumes_fixed_hosts(N):
            self._create_san_volumes(fixed_host_count, N)

        fixed_hosts_scaling = self._measure_scaling(create_n_volumes_fixed_hosts, VolumeResource)
        self.assertIsInstance(fixed_hosts_scaling, OrderN)
        self.assertEqual(fixed_hosts_scaling.queries_per_object, QUERIES_PER_VOLUME_HOST)

        # Creating N volumes with a proportional number of hosts, with all volumes visible to all hosts
        def create_n_volumes_proportional_hosts(N):
            self._create_san_volumes(N, N)

        proportional_hosts_scaling = self._measure_scaling(create_n_volumes_proportional_hosts, VolumeResource)
        self.assertIsInstance(proportional_hosts_scaling, OrderN)
        self.assertEqual(proportional_hosts_scaling.queries_per_object, QUERIES_PER_VOLUME_HOST)

        # With a fixed number of volumes, increasing the number of hosts that can see the volumes
        fixed_volume_count = 8

        def create_n_hosts_fixed_volumes(N):
            self._create_san_volumes(N, fixed_volume_count)

        scaling_with_hosts = self._measure_scaling(create_n_hosts_fixed_volumes, VolumeResource, HostResource)

        self.assertIsInstance(scaling_with_hosts, Order1)
        self.assertEqual(
            scaling_with_hosts.query_count,
            PAGING_AND_AUTH_QUERIES + QUERIES_PER_VOLUME + (fixed_volume_count * QUERIES_PER_VOLUME_HOST),
        )

    def _create_filesystem_n_osts(self, n_targets):
        assert n_targets >= 3
        ManagedFilesystem.objects.update(not_deleted=None)
        ManagedTarget.objects.update(not_deleted=None)
        ManagedTargetMount.objects.update(not_deleted=None)
        self._create_n_volumes_host_pairs(n_targets)
        assert ManagedTarget.objects.count() == 0

        fs = None
        for i, volume in enumerate(Volume.objects.all()):
            if i == 0:
                mgt, mounts = ManagedMgs.create_for_volume(volume.id)
                fs = ManagedFilesystem.objects.create(name="foo", mgs=mgt)
                ObjectCache.add(ManagedFilesystem, fs)
            elif i == 1:
                ObjectCache.add(
                    ManagedTarget, ManagedMdt.create_for_volume(volume.id, filesystem=fs)[0].managedtarget_ptr
                )
            else:
                ObjectCache.add(
                    ManagedTarget, ManagedOst.create_for_volume(volume.id, filesystem=fs)[0].managedtarget_ptr
                )

    def test_filesystem_targets(self):
        target_scaling = self._measure_scaling(self._create_filesystem_n_osts, TargetResource, TargetResource)
        self.assertIsInstance(target_scaling, OrderN)
        self.assertEqual(target_scaling.queries_per_object, QUERIES_PER_TARGET)

        filesystem_scaling = self._measure_scaling(self._create_filesystem_n_osts, FilesystemResource, TargetResource)
        self.assertIsInstance(filesystem_scaling, Order1)
