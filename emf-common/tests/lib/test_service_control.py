import mock

from emf_common.lib import util
from emf_common.lib.service_control import ServiceControl
from emf_common.lib.service_control import ServiceControlEL7
from emf_common.test.command_capture_testcase import CommandCaptureTestCase
from emf_common.test.command_capture_testcase import CommandCaptureCommand


class TestServiceStateEL7(CommandCaptureTestCase):
    def setUp(self):
        super(TestServiceStateEL7, self).setUp()

        mock.patch.object(util, "platform_info", util.PlatformInfo("Linux", "CentOS", 0.0, "7.3", 0.0, 0, "")).start()

        self.test = ServiceControl.create("test_service")
        self.assertEqual(type(self.test), ServiceControlEL7)

    # Test the start method
    def test_service_start(self):
        self.add_commands(CommandCaptureCommand(("systemctl", "start", "test_service"), executions_remaining=1))

        self.test._start()
        self.assertEqual(("systemctl", "start", "test_service"), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

    # Test the stop method
    def test_service_stop(self):
        self.add_commands(CommandCaptureCommand(("systemctl", "stop", "test_service"), executions_remaining=1))

        self.test._stop()
        self.assertEqual(("systemctl", "stop", "test_service"), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

    # Test the running method
    def test_service_running(self):
        self.add_commands(CommandCaptureCommand(("systemctl", "is-active", "test_service"), executions_remaining=1))

        self.test.running
        self.assertEqual(("systemctl", "is-active", "test_service"), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

    # Test the enabled method
    def test_service_enabled(self):
        self.add_commands(CommandCaptureCommand(("systemctl", "is-enabled", "test_service"), executions_remaining=1))

        self.test.enabled
        self.assertEqual(("systemctl", "is-enabled", "test_service"), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

        # Test the enable method

    def test_service_enable(self):
        self.add_commands(CommandCaptureCommand(("systemctl", "enable", "test_service"), executions_remaining=1))

        self.test.enable()
        self.assertEqual(("systemctl", "enable", "test_service"), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

    def test_service_daemon_reload(self):
        """
        Test the daemon_reload function for ServiceControl on el7.

        When using el7 it should issue systemctl daemon-reload command.
        """
        self.add_commands(CommandCaptureCommand(("systemctl", "daemon-reload"), executions_remaining=1))

        self.test.daemon_reload()
        self.assertEqual(self.commands_ran_count, 1)
        self.assertRanAllCommandsInOrder()

        # Test the reload method

    def test_service_reload(self):
        self.add_commands(CommandCaptureCommand(("systemctl", "reload", "test_service"), executions_remaining=1))

        self.test.reload()
        self.assertEqual(("systemctl", "reload", "test_service"), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

        # Test the disable method

    def test_service_disable(self):
        self.add_commands(CommandCaptureCommand(("systemctl", "disable", "test_service"), executions_remaining=1))

        self.test.disable()
        self.assertEqual(("systemctl", "disable", "test_service"), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)
