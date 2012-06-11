from chroma_core.models.jobs import SchedulingError
from tests.unit.chroma_core.helper import JobTestCaseWithHost, MockAgent, freshen
from chroma_core.lib.state_manager import StateManagerClient
import datetime
from dateutil import tz


class TestTransitionsWithCommands(JobTestCaseWithHost):
    def test_onejob(self):
        # Our self.host is initially lnet_up
        from chroma_core.models import ManagedHost
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        from chroma_core.models import Command

        # This tests a state transition which is done by a single job
        command_id = Command.set_state([(freshen(self.host), 'lnet_down')]).id
        self.assertEqual(Command.objects.get(pk = command_id).complete, True)
        self.assertEqual(Command.objects.get(pk = command_id).jobs.count(), 1)

        # Test that if I try to run the same again I get None
        command = Command.set_state([(freshen(self.host), 'lnet_down')])
        self.assertEqual(command, None)

    def test_2steps(self):
        from chroma_core.models import ManagedHost
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # This tests a state transition which requires two jobs acting on the same object
        from chroma_core.models import Command
        command_id = Command.set_state([(freshen(self.host), 'lnet_unloaded')]).id
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_unloaded')
        self.assertEqual(Command.objects.get(pk = command_id).complete, True)
        self.assertEqual(Command.objects.get(pk = command_id).jobs.count(), 2)


class TestStateManager(JobTestCaseWithHost):
    def test_opportunistic_execution(self):
        # Set up an MGS, leave it offline
        from chroma_core.models import ManagedMgs, ManagedMdt, ManagedOst, ManagedFilesystem
        mgt = ManagedMgs.create_for_volume(self._test_lun(self.host).id, name = "MGS")
        fs = ManagedFilesystem.objects.create(mgs = mgt, name = "testfs")
        ManagedMdt.create_for_volume(self._test_lun(self.host).id, filesystem = fs)
        ManagedOst.create_for_volume(self._test_lun(self.host).id, filesystem = fs)

        self.set_state(ManagedMgs.objects.get(pk = mgt.pk), 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'unmounted')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 0)
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 0)

        try:
            # Make it so that an MGS start operation will fail
            MockAgent.succeed = False

            import chroma_core.lib.conf_param
            chroma_core.lib.conf_param.set_conf_params(fs, {"llite.max_cached_mb": "32"})

            self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 1)
            self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 0)
        finally:
            MockAgent.succeed = True

        self.set_state(fs, 'available')
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).state, 'mounted')

        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version, 1)
        self.assertEqual(ManagedMgs.objects.get(pk = mgt.pk).conf_param_version_applied, 1)

    def test_invalid_state(self):
        with self.assertRaisesRegexp(SchedulingError, "is invalid for"):
            self.set_state(self.host, 'lnet_rhubarb')

    def test_1step(self):
        # Should be a simple one-step operation
        from chroma_core.models import ManagedHost
        # Our self.host is initially lnet_up
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # One job
        self.set_state(self.host, 'lnet_down')
        self.assertState(self.host, 'lnet_down')

        # One more job
        self.set_state(self.host, 'lnet_unloaded')
        self.assertState(self.host, 'lnet_unloaded')

    def test_notification(self):
        """Test that state notifications cause the state of an object to change"""
        self.assertState(self.host, 'lnet_up')
        now = datetime.datetime.utcnow().replace(tzinfo = tz.tzutc())
        StateManagerClient.notify_state(freshen(self.host), now, 'lnet_down', ['lnet_up'])
        self.assertEqual(freshen(self.host).state, 'lnet_down')

    def test_late_notification(self):
        """Test that notifications are droppped when they are older than
        the last change to an objects state"""
        self.assertState(self.host, 'lnet_up')
        awhile_ago = datetime.datetime.utcnow().replace(tzinfo = tz.tzutc()) - datetime.timedelta(seconds = 120)
        StateManagerClient.notify_state(freshen(self.host), awhile_ago, 'lnet_down', ['lnet_up'])
        self.assertEqual(freshen(self.host).state, 'lnet_up')

    def test_2steps(self):
        from chroma_core.models import ManagedHost
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_up')

        # This tests a state transition which requires two jobs acting on the same object
        self.set_state(self.host, 'lnet_unloaded')
        self.assertEqual(ManagedHost.objects.get(pk = self.host.pk).state, 'lnet_unloaded')
