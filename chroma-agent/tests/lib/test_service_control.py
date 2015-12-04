import mock

from chroma_agent.lib.service_control import ServiceControl
from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand


class TestServiceStateRH6(CommandCaptureTestCase):
    def setUp(self):
        super(TestServiceStateRH6, self).setUp()

        mock.patch('chroma_agent.lib.service_control.platform.system', return_value="Linux").start()
        mock.patch('chroma_agent.lib.service_control.platform.linux_distribution', return_value=('CentOS', '6.6', 'Final')).start()

        self.test_service = ServiceControl.create('test_service')

    # Test that the service starts successfully when the start method is called
    def test_service_start_success(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'start')),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status')))

        response = self.test_service.start(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, None)
        self.assertEqual(self.commands_ran_count, 2)

    # Test that the expected outcome is correct when the service starts but keeps failing validation,
    #  when the start method is called
    def test_service_start_validate_fail(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'start')),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'),
                                                rc=1))

        response = self.test_service.start(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, 'Service test_service is not running after being started')
        self.assertEqual(self.commands_ran_count, 12)

    # Test that the expected outcome is correct when the service fails to start,
    # retries then starts but doesnt pass validation , retries then starts and passes validation
    def test_service_start_initial_fail(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'start'),
                                                rc=1, stderr='Service Failed To Start', executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'start'), executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'),
                                                rc=1, executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'start'), executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'), executions_remaining=1))
        response = self.test_service.start(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()

    # Test that the expected outcome is correct when the service fails to stop,
    #  retries then stops but doesnt pass validation , retries then stops and passes validation
    def test_service_stop_initial_fail(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'stop'),
                                                rc=1, stderr='Service Failed To Stop', executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'stop'), executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'),
                                                rc=0, executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'stop'), executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'), rc=1,
                                                executions_remaining=1))

        response = self.test_service.stop(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()

    # Test that the expected outcome is correct when the service fails to stop, when the stop method is called
    def test_service_stop_validate_fail(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'stop')),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'),
                                                rc=0))

        response = self.test_service.stop(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response,
                         'Service test_service is still running after being stopped')
        self.assertEqual(self.commands_ran_count, 12)

    # Test that the expected outcome is correct when the service successful restarts when the restart method is called
    def test_service_restart_success(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'stop'), executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'), rc=1, executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'start'), executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'), executions_remaining=1)
                          )

        response = self.test_service.restart(retry_time=0.1, validate_time=0.1)
        self.assertEqual(response, None)
        self.assertRanAllCommandsInOrder()

    # Test that the expected outcome is correct when restart fails by failing to stop the service
    def test_service_restart_failstop(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'stop'),
                                                rc=1, stderr='Service Failed To Stop'))

        response = self.test_service.restart(retry_time=0.1, validate_time=0.1)
        self.assertEqual(response, "Error (1) running '/sbin/service test_service stop': '' 'Service Failed To Stop'")
        self.assertEqual(self.commands_ran_count, 6)

    # Test that the expected outcome is correct when enabling the service
    def test_service_enable_success(self):
        self.add_commands(CommandCaptureCommand(('/sbin/chkconfig', 'test_service', 'on'), executions_remaining=1))

        response = self.test_service.enable()
        self.assertEqual(response, None)
        self.assertEqual(self.commands_ran_count, 1)

    # Test that the expected outcome is correct when disabling the service
    def test_service_disable_success(self):
        self.add_commands(CommandCaptureCommand(('/sbin/chkconfig', 'test_service', 'off'), executions_remaining=1))

        response = self.test_service.disable()
        self.assertEqual(response, None)
        self.assertEqual(self.commands_ran_count, 1)
