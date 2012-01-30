
from tests.unit.configure.helper import JobTestCase, MockAgent


class JobTestCaseWithHost(JobTestCase):
    mock_servers = {
            'myaddress': {
                'fqdn': 'myaddress.mycompany.com',
                'nids': ["192.168.0.1@tcp"]
            }
    }

    def setUp(self):
        super(JobTestCaseWithHost, self).setUp()

        from configure.models import ManagedHost
        self.host = ManagedHost.create_from_string(self.mock_servers.items()[0][0])
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).lnetconfiguration.state, 'nids_known')


class TestTransitionsWithCommands(JobTestCaseWithHost):
    def test_onejob(self):
        # Our self.host is initially lnet_up
        from configure.models import ManagedHost
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        from configure.models import Command

        # This tests a state transition which is done by a single job
        command_id = Command.set_state(self.host, 'lnet_down').id
        self.assertEqual(Command.objects.get(pk = command_id).jobs_created, True)
        self.assertEqual(Command.objects.get(pk = command_id).complete, True)
        self.assertEqual(Command.objects.get(pk = command_id).jobs.count(), 1)

        command_id = Command.set_state(self.host, 'lnet_down').id
        self.assertEqual(Command.objects.get(pk = command_id).jobs_created, True)
        self.assertEqual(Command.objects.get(pk = command_id).complete, True)
        self.assertEqual(Command.objects.get(pk = command_id).jobs.count(), 0)

    def test_2steps(self):
        from configure.models import ManagedHost
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # This tests a state transition which requires two jobs acting on the same object
        from configure.models import Command
        command_id = Command.set_state(self.host, 'lnet_unloaded').id
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_unloaded')
        self.assertEqual(Command.objects.get(pk = command_id).jobs_created, True)
        self.assertEqual(Command.objects.get(pk = command_id).complete, True)
        self.assertEqual(Command.objects.get(pk = command_id).jobs.count(), 2)


class TestFSTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestFSTransitions, self).setUp()

        from hydraapi.filesystem import create_fs
        from hydraapi.target import create_target
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        self.mgt = create_target(self._test_lun(self.host).id, ManagedMgs, name = "MGS")
        self.fs = create_fs(self.mgt.pk, "testfs", {})
        self.mdt = create_target(self._test_lun(self.host).id, ManagedMdt, filesystem = self.fs)
        self.ost = create_target(self._test_lun(self.host).id, ManagedOst, filesystem = self.fs)

        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unformatted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'unformatted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'unformatted')

        from configure.lib.state_manager import StateManager
        StateManager.set_state(self.fs, 'available')

        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'mounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'available')

    def test_mgs_removal(self):
        """Test that removing an MGS takes the filesystems with it"""
        from configure.lib.state_manager import StateManager
        StateManager.set_state(self.mgt, 'removed')

    def test_fs_removal(self):
        """Test that removing a filesystem takes its targets with it"""
        from configure.lib.state_manager import StateManager
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        StateManager.set_state(self.fs, 'removed')

        # FIXME: Hey, why is this MGS getting unmounted when I remove the filesystem?
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unmounted')

        with self.assertRaises(ManagedMdt.DoesNotExist):
            ManagedMdt.objects.get(pk = self.mdt.pk)
        self.assertEqual(ManagedMdt._base_manager.get(pk = self.mdt.pk).state, 'removed')
        with self.assertRaises(ManagedOst.DoesNotExist):
            ManagedOst.objects.get(pk = self.ost.pk)
        self.assertEqual(ManagedOst._base_manager.get(pk = self.ost.pk).state, 'removed')
        with self.assertRaises(ManagedFilesystem.DoesNotExist):
            ManagedFilesystem.objects.get(pk = self.fs.pk)

    def test_target_stop(self):
        from configure.lib.state_manager import StateManager
        from configure.models import ManagedMdt, ManagedFilesystem
        StateManager.set_state(ManagedMdt.objects.get(pk = self.mdt.pk), 'unmounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'unmounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'unavailable')

    def test_stop_start(self):
        from configure.lib.state_manager import StateManager
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        StateManager.set_state(self.fs, 'stopped')

        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unmounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'unmounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'unmounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'stopped')

        StateManager.set_state(self.fs, 'available')

        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')
        self.assertEqual(ManagedMdt.objects.get(pk = self.mdt.pk).state, 'mounted')
        self.assertEqual(ManagedOst.objects.get(pk = self.ost.pk).state, 'mounted')
        self.assertEqual(ManagedFilesystem.objects.get(pk = self.fs.pk).state, 'available')


class TestTargetTransitions(JobTestCaseWithHost):
    def setUp(self):
        super(TestTargetTransitions, self).setUp()

        from hydraapi.target import create_target
        from configure.models import ManagedMgs
        from configure.lib.state_manager import StateManager
        self.mgt = create_target(self._test_lun(self.host).id, ManagedMgs, name = "MGS")
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unformatted')
        StateManager.set_state(self.mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')

    def test_start_stop(self):
        from configure.lib.state_manager import StateManager
        from configure.models import ManagedMgs
        StateManager.set_state(self.mgt, 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'unmounted')
        StateManager.set_state(self.mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = self.mgt.pk).state, 'mounted')

    def test_removal(self):
        from configure.lib.state_manager import StateManager
        from configure.models import ManagedMgs
        StateManager.set_state(self.mgt, 'removed')
        with self.assertRaises(ManagedMgs.DoesNotExist):
            ManagedMgs.objects.get(pk = self.mgt.pk)
        self.assertEqual(ManagedMgs._base_manager.get(pk = self.mgt.pk).state, 'removed')

    def test_removal_mount_dependency(self):
        """Test that when removing, if target mounts cannot be unconfigured,
        the target is not removed"""
        from configure.lib.state_manager import StateManager
        from configure.models import ManagedMgs

        try:
            # Make it so that the mount unconfigure operations will fail
            MockAgent.succeed = False

            # -> the TargetMount removal parts of this operation will fail, we
            # want to make sure that this means that Target deletion part
            # fails as well
            StateManager.set_state(self.mgt, 'removed')

            ManagedMgs.objects.get(pk = self.mgt.pk)
            self.assertNotEqual(ManagedMgs._base_manager.get(pk = self.mgt.pk).state, 'removed')
        finally:
            MockAgent.succeed = True

        # Now let the op go through successfully
        StateManager.set_state(self.mgt, 'removed')
        with self.assertRaises(ManagedMgs.DoesNotExist):
            ManagedMgs.objects.get(pk = self.mgt.pk)
        self.assertEqual(ManagedMgs._base_manager.get(pk = self.mgt.pk).state, 'removed')


class TestStateManager(JobTestCaseWithHost):
    def test_opportunistic_execution(self):
        # Set up an MGS, leave it offline
        from hydraapi.filesystem import create_fs
        from hydraapi.target import create_target
        from configure.models import ManagedMgs, ManagedMdt, ManagedOst
        mgt = create_target(self._test_lun(self.host).id, ManagedMgs, name = "MGS")
        fs = create_fs(mgt.pk, "testfs", {})
        create_target(self._test_lun(self.host).id, ManagedMdt, filesystem = fs)
        create_target(self._test_lun(self.host).id, ManagedOst, filesystem = fs)

        from configure.lib.state_manager import StateManager
        StateManager.set_state(ManagedMgs.objects.get(pk = mgt.pk), 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 0)
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 0)

        try:
            # Make it so that an MGS start operation will fail
            MockAgent.succeed = False

            from hydraapi.configureapi import set_target_conf_param
            params = {"llite.max_cached_mb": "32"}
            set_target_conf_param(fs.pk, params, True)

            self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 1)
            self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 0)
        finally:
            MockAgent.succeed = True

        StateManager.set_state(mgt, 'mounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 1)
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 1)

    def test_invalid_state(self):
        from configure.lib.state_manager import StateManager
        with self.assertRaisesRegexp(RuntimeError, "is invalid for"):
            StateManager.set_state(self.host, 'lnet_rhubarb')

    def test_1step(self):
        # Should be a simple one-step operation
        from configure.lib.state_manager import StateManager
        from configure.models import ManagedHost
        # Our self.host is initially lnet_up
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # This tests a state transition which is done by a single job
        StateManager.set_state(self.host, 'lnet_down')
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_down')

    def test_2steps(self):
        from configure.lib.state_manager import StateManager
        from configure.models import ManagedHost
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # This tests a state transition which requires two jobs acting on the same object
        StateManager.set_state(self.host, 'lnet_unloaded')
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_unloaded')
