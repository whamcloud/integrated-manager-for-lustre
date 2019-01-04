from django.db import connection
from chroma_core.lib.util import dbperf
from chroma_core.models.host import Volume, VolumeNode
from chroma_core.models.storage_plugin import StorageResourceRecord
from tests.unit.chroma_core.lib.storage_plugin.resource_manager.test_resource_manager import ResourceManagerTestCase


class TestManyObjects(ResourceManagerTestCase):
    """
    This test is not for correctness: mainly useful as a way of tuning/measuring the number of queries
    being done by the resource manager & how it varies with the number of devices in play
    """

    def setUp(self):
        super(TestManyObjects, self).setUp("linux")

        resource_record, scannable_resource = self._make_global_resource(
            "linux", "PluginAgentResources", {"plugin_name": "linux", "host_id": self.host.id}
        )

        couplet_record, couplet_resource = self._make_global_resource(
            "example_plugin", "Couplet", {"address_1": "foo", "address_2": "bar"}
        )

        self.host_resource_pk = resource_record.pk
        self.couplet_resource_pk = couplet_record.pk

        # luns
        self.N = 4
        # drives per lun
        self.M = 10
        self.host_resources = [scannable_resource]
        self.controller_resources = [couplet_resource]
        lun_size = 1024 * 1024 * 1024 * 73
        for n in range(0, self.N):
            drives = []
            for m in range(0, self.M):
                drive_resource = self._make_local_resource(
                    "example_plugin", "HardDrive", serial_number="foobarbaz%s_%s" % (n, m), capacity=lun_size / self.M
                )
                drives.append(drive_resource)
            lun_resource = self._make_local_resource(
                "example_plugin",
                "Lun",
                parents=drives,
                serial="foobar%d" % n,
                local_id=n,
                size=lun_size,
                name="LUN_%d" % n,
            )
            self.controller_resources.extend(drives + [lun_resource])

            dev_resource = self._make_local_resource("linux", "ScsiDevice", serial="foobar%d" % n, size=lun_size)
            node_resource = self._make_local_resource(
                "linux", "LinuxDeviceNode", path="/dev/foo%s" % n, parents=[dev_resource], host_id=self.host.id
            )
            self.host_resources.extend([dev_resource, node_resource])

    def test_global_remove(self):
        try:
            dbperf.enabled = True
            connection.use_debug_cursor = True

            with dbperf("session_open_host"):
                self.resource_manager.session_open(self.plugin, self.host_resource_pk, self.host_resources, 60)
            with dbperf("session_open_controller"):
                self.resource_manager.session_open(self.plugin, self.couplet_resource_pk, self.controller_resources, 60)

            host_res_count = self.N * 2 + 1
            cont_res_count = self.N + self.N * self.M + 1
            self.assertEqual(StorageResourceRecord.objects.count(), host_res_count + cont_res_count)
            self.assertEqual(Volume.objects.count(), self.N)
            self.assertEqual(VolumeNode.objects.count(), self.N)

            with dbperf("global_remove_resource_host"):
                self.resource_manager.global_remove_resource(self.host_resource_pk)

            self.assertEqual(StorageResourceRecord.objects.count(), cont_res_count)

            with dbperf("global_remove_resource_controller"):
                self.resource_manager.global_remove_resource(self.couplet_resource_pk)

            self.assertEqual(StorageResourceRecord.objects.count(), 0)

        finally:
            dbperf.enabled = False
            connection.use_debug_cursor = False
