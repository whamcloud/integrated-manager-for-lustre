import mock

from tests.unit.chroma_core.helpers import synthetic_host
from tests.unit.chroma_core.helpers import load_default_profile
from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase
from chroma_core.models import HostContactAlert, HostOfflineAlert, ServerProfile
from chroma_core.models import (
    ManagedTarget,
    FailoverTargetJob,
    RebootHostJob,
    ShutdownHostJob,
    PoweronHostJob,
    PoweroffHostJob,
    PowercycleHostJob,
    MountLustreFilesystemsJob,
    UnmountLustreFilesystemsJob,
    CreateOstPoolJob,
    DestroyOstPoolJob,
)
from chroma_core.lib.cache import ObjectCache


class TestAdvertisedCase(IMLUnitTestCase):
    normal_host_state = "managed"

    def set_managed(self, managed):
        self.host.immutable_state = not managed
        self.host.server_profile.managed = managed
        self.host.server_profile.corosync = managed
        self.host.server_profile.corosync2 = False
        self.host.server_profile.ntp = managed


class TestAdvertisedJobCoverage(TestAdvertisedCase):
    def test_all_advertised_jobs_tested(self):
        import inspect
        from chroma_core.models.jobs import AdvertisedJob

        # This just tests that we're testing all advertised jobs. Will fail
        # if someone adds a new AdvertisedJob that isn't covered.
        #
        # Reasonable exceptions are those jobs which can always run,
        # or jobs that are parents for implementing subclasses.
        EXCEPTIONS = [
            "ForceRemoveHostJob",
            "ForceRemoveCopytoolJob",
            "MigrateTargetJob",
            "CreateOstPoolJob",
            "DestroyOstPoolJob",
            "CreateTaskJob",
            "RemoveTaskJob",
        ]
        IMPORTED_JOBS = [x for x in globals().values() if (inspect.isclass(x) and issubclass(x, AdvertisedJob))]

        def _find_children(cls):
            children = []
            for child in cls.__subclasses__():
                children.append(child)
                children.extend(_find_children(child))
            return children

        missing = set()
        for child in _find_children(AdvertisedJob):
            if child not in IMPORTED_JOBS and child.__name__ not in EXCEPTIONS:
                missing.add(child)

        self.assertItemsEqual(missing, set())


class TestAdvertisedTargetJobs(TestAdvertisedCase):
    def setUp(self):
        super(TestAdvertisedTargetJobs, self).setUp()

        load_default_profile()

        self.target = mock.Mock()
        self.target.immutable_state = False
        self.target.primary_host = synthetic_host()
        self.target.active_host = self.target.primary_host
        self.target.inactive_hosts = [synthetic_host()]

    def test_FailoverTargetJob(self):
        # Normal situation
        self.assertTrue(FailoverTargetJob.can_run(self.target))

        # Failover
        self.target.inactive_hosts = []
        self.assertFalse(FailoverTargetJob.can_run(self.target))

        # Monitor-only
        self.target.active_host = self.target.primary_host
        self.target.immutable_state = True
        self.assertFalse(FailoverTargetJob.can_run(self.target))


class TestAdvertisedHostJobs(TestAdvertisedCase):
    def setUp(self):
        super(TestAdvertisedHostJobs, self).setUp()

        load_default_profile()

        self.host = synthetic_host()
        self.set_managed(True)
        self.host.state = self.normal_host_state

    def test_RebootHostJob(self):
        # Normal situation
        self.assertTrue(RebootHostJob.can_run(self.host))

        # Bad states
        for state in ["removed", "undeployed", "unconfigured"]:
            self.host.state = state
            self.assertFalse(RebootHostJob.can_run(self.host))
            self.host.state = self.normal_host_state

        # Active host alerts
        for klass in [HostOfflineAlert, HostContactAlert]:
            klass.notify(self.host, True)
            self.assertFalse(RebootHostJob.can_run(self.host))
            klass.notify(self.host, False)

        # Monitor-only host
        self.set_managed(False)
        self.assertFalse(RebootHostJob.can_run(self.host))

    def test_ShutdownHostJob(self):
        # Normal situation
        self.assertTrue(ShutdownHostJob.can_run(self.host))

        # Bad states
        for state in ["removed", "undeployed", "unconfigured"]:
            self.host.state = state
            self.assertFalse(ShutdownHostJob.can_run(self.host))
            self.host.state = self.normal_host_state

        # Active host alerts
        for klass in [HostOfflineAlert, HostContactAlert]:
            klass.notify(self.host, True)
            self.assertFalse(ShutdownHostJob.can_run(self.host))
            klass.notify(self.host, False)

        # Monitor-only host
        self.set_managed(False)
        self.assertFalse(ShutdownHostJob.can_run(self.host))


class TestAdvertisedPowerJobs(TestAdvertisedCase):
    def setUp(self):
        super(TestAdvertisedPowerJobs, self).setUp()

        self.host = mock.Mock()
        self.set_managed(True)

        self.host.outlet_list = [mock.MagicMock(has_power=True), mock.MagicMock(has_power=True)]

        self.host.outlets = mock.Mock()

        def all():
            return self.host.outlet_list

        self.host.outlets.all = all

        def count():
            return len(self.host.outlet_list)

        self.host.outlets.count = count

    def test_PoweronHostJob(self):
        # Normal situation, all outlets have power
        self.assertFalse(PoweronHostJob.can_run(self.host))

        # One outlet has power
        self.host.outlet_list[0].has_power = False
        self.assertFalse(PoweronHostJob.can_run(self.host))

        # No outlets have power
        self.host.outlet_list[1].has_power = False
        self.assertTrue(PoweronHostJob.can_run(self.host))

        # Monitor-only host
        self.set_managed(False)
        self.assertFalse(PoweronHostJob.can_run(self.host))
        self.set_managed(True)

        # One outlet off, one unknown
        self.host.outlet_list[1].has_power = None
        self.assertTrue(PoweronHostJob.can_run(self.host))

        # One outlet on, one unknown
        self.host.outlet_list[0].has_power = True
        self.assertFalse(PoweronHostJob.can_run(self.host))

        # Both outlets unknown
        self.host.outlet_list[0].has_power = None
        self.assertFalse(PoweronHostJob.can_run(self.host))

        # No outlets associated
        self.host.outlet_list[:] = []
        self.assertFalse(PoweronHostJob.can_run(self.host))

    def test_PoweroffHostJob(self):
        # Monitor-only host
        self.set_managed(False)
        self.assertFalse(PowercycleHostJob.can_run(self.host))
        self.set_managed(True)

        # Normal situation, all outlets have power
        self.assertTrue(PoweroffHostJob.can_run(self.host))

        # One outlet has power
        self.host.outlet_list[0].has_power = False
        self.assertTrue(PoweroffHostJob.can_run(self.host))

        # No outlets have power
        self.host.outlet_list[1].has_power = False
        self.assertFalse(PoweroffHostJob.can_run(self.host))

        # One outlet off, one unknown
        self.host.outlet_list[1].has_power = None
        self.assertFalse(PoweroffHostJob.can_run(self.host))

        # One outlet on, one unknown
        self.host.outlet_list[0].has_power = True
        self.assertFalse(PoweroffHostJob.can_run(self.host))

        # Both outlets unknown
        self.host.outlet_list[0].has_power = None
        self.assertFalse(PoweroffHostJob.can_run(self.host))

        # No outlets associated
        self.host.outlet_list[:] = []
        self.assertFalse(PoweronHostJob.can_run(self.host))

    def test_PowercycleHostJob(self):
        # Monitor-only host
        self.set_managed(False)
        self.assertFalse(PowercycleHostJob.can_run(self.host))
        self.set_managed(True)

        # Normal situation, all outlets have power
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # One outlet has power
        self.host.outlet_list[0].has_power = False
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # No outlets have power
        self.host.outlet_list[1].has_power = False
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # One outlet off, one unknown
        self.host.outlet_list[1].has_power = None
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # One outlet on, one unknown
        self.host.outlet_list[0].has_power = True
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # Both outlets unknown
        self.host.outlet_list[0].has_power = None
        self.assertTrue(PowercycleHostJob.can_run(self.host))

        # No outlets associated
        self.host.outlet_list[:] = []
        self.assertFalse(PoweronHostJob.can_run(self.host))


class TestClientManagementJobs(TestAdvertisedCase):
    def load_worker_profile(self):
        worker_profile = ServerProfile(
            name="test_worker_profile",
            ui_name="Managed Lustre client",
            ui_description="Client available for IML admin tasks",
            managed=True,
            worker=True,
            initial_state="managed",
        )
        worker_profile.save()
        return worker_profile

    def create_fake_filesystem_client(self, active=False):
        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem, LustreClientMount
        from tests.unit.chroma_core.helpers import synthetic_volume_full

        # mgt, _ = ManagedMgs.create_for_volume(synthetic_volume_full(self.server).id, name="MGS")
        # fs = ManagedFilesystem.objects.create(mgs=mgt, name="testfs")
        # ObjectCache.add(ManagedFilesystem, fs)
        # ManagedMdt.create_for_volume(synthetic_volume_full(self.server).id, filesystem=fs)
        # ManagedOst.create_for_volume(synthetic_volume_full(self.server).id, filesystem=fs)

        mgt_target = ManagedTarget.objects.create(
            id=1,
            state_modified_at='2020-11-11T23:52:23.938603+00:00',
            state="unformatted",
            immutable_state=False,
            name="MGS",
            uuid=None,
            ha_label=None,
            inode_size=None,
            bytes_per_inode=None,
            inode_count=None,
            reformat=False,
            not_deleted=True,
        );
        mgt_target.save()

        mgt = ManagedMgs.objects.create(managedtarget_ptr_id=1, conf_param_version=0, conf_param_version_applied=0)
        mgt.save()

        fs = ManagedFilesystem.objects.create(mgs=mgt, name="testfs", id=1, mdt_next_index=1, ost_next_index=1)
        ObjectCache.add(ManagedFilesystem, fs)

        mdt_target = ManagedTarget.objects.create(
            id=2,
            state_modified_at='2020-11-11T23:52:23.938603+00:00',
            state="unformatted",
            immutable_state=False,
            name="testfs-MDT0000",
            uuid=None,
            ha_label=None,
            inode_size=None,
            bytes_per_inode=None,
            inode_count=None,
            reformat=False,
            not_deleted=True,
        );
        mdt_target.save()

        mdt = ManagedMdt.objects.create(managedtarget_ptr_id=2, index=0, filesystem_id=1)
        mdt.save()

        ost_target = ManagedTarget.objects.create(
            id=3,
            state_modified_at='2020-11-11T23:52:23.938603+00:00',
            state="unformatted",
            immutable_state=False,
            name="foo-OST0000",
            uuid=None,
            ha_label=None,
            inode_size=None,
            bytes_per_inode=None,
            inode_count=None,
            reformat=False,
            not_deleted=True,
        );
        ost_target.save()

        ost = ManagedOst.objects.create(managedtarget_ptr_id=3, index=0, filesystem_id=1)
        ost.save()

        state = "mounted" if active else "unmounted"
        self.mount = LustreClientMount.objects.create(host=self.worker, filesystem=fs.name, state=state)

        ObjectCache.add(LustreClientMount, self.mount)

    def toggle_fake_client_state(self):
        state = "mounted" if not self.mount.active else "unmounted"
        self.mount.state = state
        self.mount.save()
        ObjectCache.update(self.mount)

    def setUp(self):
        super(TestClientManagementJobs, self).setUp()

        load_default_profile()
        worker_profile = self.load_worker_profile()
        self.worker = synthetic_host(server_profile=worker_profile.name)
        self.worker.immutable_state = False
        self.worker.state = self.normal_host_state

        self.server = synthetic_host()
        self.server.immutable_state = False
        self.server.state = self.normal_host_state

        # If the test that just ran imported storage_plugin_manager, it will
        # have instantiated its singleton, and created some DB records.
        # Django TestCase rolls back the database, so make sure that we
        # also roll back (reset) this singleton.
        import chroma_core.lib.storage_plugin.manager

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = (
            chroma_core.lib.storage_plugin.manager.StoragePluginManager()
        )

    def tearDown(self):
        super(TestClientManagementJobs, self).tearDown()

        # clear out the singleton to avoid polluting other tests
        ObjectCache.clear()

    def test_MountLustreFilesystemsJob(self):
        # Servers should never be able to run this job
        self.assertFalse(MountLustreFilesystemsJob.can_run(self.server))

        # Worker nodes should not be able to run this job if not
        # associated with a filesystem
        self.assertFalse(MountLustreFilesystemsJob.can_run(self.worker))

        # Worker nodes should be able to run this job if associated
        # but the associated filesystem hasn't been mounted
        self.create_fake_filesystem_client(active=False)
        self.assertTrue(MountLustreFilesystemsJob.can_run(self.worker))

        # Bad states
        for state in ["removed", "undeployed", "unconfigured"]:
            self.worker.state = state
            self.assertFalse(MountLustreFilesystemsJob.can_run(self.worker))
            self.worker.state = self.normal_host_state

        # Active host alerts
        for klass in [HostOfflineAlert, HostContactAlert]:
            klass.notify(self.worker, True)
            self.assertFalse(MountLustreFilesystemsJob.can_run(self.worker))
            klass.notify(self.worker, False)

        # Associated filesystem already mounted
        self.toggle_fake_client_state()
        self.assertFalse(MountLustreFilesystemsJob.can_run(self.worker))

    def test_UnmountLustreFilesystemsJob(self):
        # Servers should never be able to run this job
        self.assertFalse(UnmountLustreFilesystemsJob.can_run(self.server))

        # Worker nodes should not be able to run this job if not
        # associated with a filesystem
        self.assertFalse(UnmountLustreFilesystemsJob.can_run(self.worker))

        # Worker nodes should be able to run this job if associated
        # and the associated filesystem is mounted
        self.create_fake_filesystem_client(active=True)
        self.assertTrue(UnmountLustreFilesystemsJob.can_run(self.worker))

        # Bad states
        for state in ["removed", "undeployed", "unconfigured"]:
            self.worker.state = state
            self.assertFalse(UnmountLustreFilesystemsJob.can_run(self.worker))
            self.worker.state = self.normal_host_state

        # Active host alerts
        for klass in [HostOfflineAlert, HostContactAlert]:
            klass.notify(self.worker, True)
            self.assertFalse(UnmountLustreFilesystemsJob.can_run(self.worker))
            klass.notify(self.worker, False)

        # Associated filesystem already Unmounted
        self.toggle_fake_client_state()
        self.assertFalse(UnmountLustreFilesystemsJob.can_run(self.worker))
