import mock

from chroma_common.lib import util
from chroma_common.lib.service_control import ServiceControl
from chroma_common.lib.service_control import ServiceControlEL6
from chroma_common.lib.service_control import ServiceControlEL7
from chroma_common.test.command_capture_testcase import CommandCaptureTestCase
from chroma_common.test.command_capture_testcase import CommandCaptureCommand


class TestServiceStateEL6(CommandCaptureTestCase):
    """Test the base class and EL6 subclass functionality, base class only needs to be tested in
    this class, features like retry and callback registration exist in base class
    """

    def setUp(self):
        super(TestServiceStateEL6, self).setUp()

        mock.patch.object(util, 'platform_info', util.PlatformInfo('Linux',
                                                                   'CentOS',
                                                                   0.0,
                                                                   '6.6',
                                                                   0.0,
                                                                   0,
                                                                   '')).start()

        self.test_service = ServiceControl.create('test_service')
        self.assertEqual(type(self.test_service), ServiceControlEL6)

    # Test that the service starts successfully when the start method is called
    def test_service_start_success(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'start')),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status')))

        response = self.test_service.start(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, None)
        self.assertEqual(self.commands_ran_count, 2)

    # Test that the service stops successfully when the stop method is called
    def test_service_stop_success(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'stop'),
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'),
                                                rc=1, executions_remaining=1))

        response = self.test_service.stop(retry_time=0.1, validate_time=0.1)

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
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'), executions_remaining=1))

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
        self.add_commands(CommandCaptureCommand(('/sbin/chkconfig', '--add', 'test_service'),
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/chkconfig', 'test_service', 'on'),
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/chkconfig', 'test_service'),
                                                executions_remaining=1))

        response = self.test_service.enable()
        self.assertEqual(response, None)

        response = self.test_service.enabled
        self.assertEqual(response, True)
        self.assertRanAllCommandsInOrder()

    # Test that the expected outcome is correct when disabling the service
    def test_service_disable_success(self):
        self.add_commands(CommandCaptureCommand(('/sbin/chkconfig', 'test_service', 'off'),
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/chkconfig', 'test_service'),
                                                rc=1, executions_remaining=1))

        response = self.test_service.disable()
        self.assertEqual(response, None)

        response = self.test_service.enabled
        self.assertEqual(response, False)
        self.assertRanAllCommandsInOrder()

    def test_service_daemon_reload(self):
        """
        Test the daemon_reload function for ServiceControl.

        By default when using el6 as the test vehicle is does nothing.
        """
        self.test_service.daemon_reload()
        self.assertEqual(self.commands_ran_count, 0)
        self.assertRanAllCommandsInOrder()

    # example callback function
    def example_func(self, service, action_code):
        self.received_codes.append((service,
                                    ServiceControl.ServiceState.reverse_mapping[action_code]))
        return None

    # Test that callback can be registered and that correct messages are received
    def test_service_register_listener_and_receive_success(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'start'),
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'),
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'stop'),
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'),
                                                rc=1, executions_remaining=1))

        self.received_codes = []

        ServiceControl.register_listener('test_service', self.example_func)

        response = self.test_service.start(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, None)
        self.assertListEqual(self.received_codes, [('test_service', 'SERVICESTARTING'),
                                                   ('test_service', 'SERVICESTARTED')])

        self.received_codes = []
        response = self.test_service.stop(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, None)
        self.assertListEqual(self.received_codes, [('test_service', 'SERVICESTOPPING'),
                                                   ('test_service', 'SERVICESTOPPED')])

    # Test that callback can be registered and that correct messages are received on control fail
    def test_service_register_listener_and_receive_fail_validation(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'start')),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'),
                                                rc=1))

        self.received_codes = []

        ServiceControl.register_listener('test_service', self.example_func)

        response = self.test_service.start(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, 'Service test_service is not running after being started')
        self.assertListEqual(self.received_codes, [('test_service', 'SERVICESTARTING'),
                                                   ('test_service', 'SERVICESTARTERROR')])

        # reset so we can test both stop and start fail validation within same test
        self.reset_command_capture()
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'stop')),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'status'),
                                                rc=0))
        self.received_codes = []
        response = self.test_service.stop(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, 'Service test_service is still running after being stopped')
        self.assertListEqual(self.received_codes, [('test_service', 'SERVICESTOPPING'),
                                                   ('test_service', 'SERVICESTOPERROR')])

    # Test that callback can be registered and that correct messages are received on control fail
    def test_service_register_listener_and_receive_fail_initial(self):
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'start'),
                                                rc=1, stderr='Service Failed To Start',
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'start'),
                                                rc=1, stderr='Service Failed To Start',
                                                executions_remaining=1))

        self.received_codes = []

        ServiceControl.register_listener('test_service', self.example_func)

        response = self.test_service.start(retry_time=0.1, validate_time=0.1, retry_count=1)

        self.assertEqual(response, "Error (1) running '/sbin/service test_service start': '' 'Service Failed To Start'")
        self.assertListEqual(self.received_codes, [('test_service', 'SERVICESTARTING'),
                                                   ('test_service', 'SERVICESTARTERROR')])

        # reset so we can test both stop and start fail validation within same test
        self.reset_command_capture()
        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service', 'stop'),
                                                rc=1, stderr='Service Failed To Stop',
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service', 'stop'),
                                                rc=1, stderr='Service Failed To Stop',
                                                executions_remaining=1))

        self.received_codes = []
        response = self.test_service.stop(retry_time=0.1, validate_time=0.1, retry_count=1)

        self.assertEqual(response, "Error (1) running '/sbin/service test_service stop': '' 'Service Failed To Stop'")
        self.assertListEqual(self.received_codes, [('test_service', 'SERVICESTOPPING'),
                                                   ('test_service', 'SERVICESTOPERROR')])

    # Test registering a callback on a service before any ServiceControl instantiated for that
    # service. Also tests unregistering callback function from service notifications.
    def test_register_before_instance(self):
        ServiceControl.register_listener('test_service_2', self.example_func)

        test_service_2 = ServiceControl.create('test_service_2')

        self.add_commands(CommandCaptureCommand(('/sbin/service', 'test_service_2', 'start'),
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service_2', 'status'),
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service_2', 'stop'),
                                                executions_remaining=1),
                          CommandCaptureCommand(('/sbin/service', 'test_service_2', 'status'),
                                                rc=1, executions_remaining=1))

        self.received_codes = []

        response = test_service_2.start(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, None)
        self.assertListEqual(self.received_codes, [('test_service_2', 'SERVICESTARTING'),
                                                   ('test_service_2', 'SERVICESTARTED')])

        self.received_codes = []

        ServiceControl.unregister_listener('test_service_2', self.example_func)

        response = test_service_2.stop(retry_time=0.1, validate_time=0.1)

        self.assertEqual(response, None)
        self.assertListEqual(self.received_codes, [])


class TestServiceStateEL7(CommandCaptureTestCase):
    def setUp(self):
        super(TestServiceStateEL7, self).setUp()

        mock.patch.object(util, 'platform_info', util.PlatformInfo('Linux',
                                                                   'CentOS',
                                                                   0.0,
                                                                   '7.2',
                                                                   0.0,
                                                                   0,
                                                                   '')).start()

        self.test = ServiceControl.create('test_service')
        self.assertEqual(type(self.test), ServiceControlEL7)

    # Test the start method
    def test_service_start(self):
        self.add_commands(CommandCaptureCommand(('systemctl', 'start', 'test_service'), executions_remaining=1))

        self.test._start()
        self.assertEqual(('systemctl', 'start', 'test_service'), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

    # Test the stop method
    def test_service_stop(self):
        self.add_commands(CommandCaptureCommand(('systemctl', 'stop', 'test_service'), executions_remaining=1))

        self.test._stop()
        self.assertEqual(('systemctl', 'stop', 'test_service'), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

    # Test the running method
    def test_service_running(self):
        self.add_commands(CommandCaptureCommand(('systemctl', 'is-active', 'test_service'), executions_remaining=1))

        self.test.running
        self.assertEqual(('systemctl', 'is-active', 'test_service'), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

    # Test the enabled method
    def test_service_enabled(self):
        self.add_commands(CommandCaptureCommand(('systemctl', 'is-enabled', 'test_service'), executions_remaining=1))

        self.test.enabled
        self.assertEqual(('systemctl', 'is-enabled', 'test_service'), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

        # Test the enable method
    def test_service_enable(self):
        self.add_commands(CommandCaptureCommand(('systemctl', 'enable', 'test_service'), executions_remaining=1))

        self.test.enable()
        self.assertEqual(('systemctl', 'enable', 'test_service'), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

    def test_service_daemon_reload(self):
        """
        Test the daemon_reload function for ServiceControl on el7.

        When using el7 it should issue systemctl daemon-reload command.
        """
        self.add_commands(CommandCaptureCommand(('systemctl', 'daemon-reload'), executions_remaining=1))

        self.test.daemon_reload()
        self.assertEqual(self.commands_ran_count, 1)
        self.assertRanAllCommandsInOrder()

        # Test the reload method
    def test_service_reload(self):
        self.add_commands(CommandCaptureCommand(('systemctl', 'reload', 'test_service'), executions_remaining=1))

        self.test.reload()
        self.assertEqual(('systemctl', 'reload', 'test_service'), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)

        # Test the disable method
    def test_service_disable(self):
        self.add_commands(CommandCaptureCommand(('systemctl', 'disable', 'test_service'), executions_remaining=1))

        self.test.disable()
        self.assertEqual(('systemctl', 'disable', 'test_service'), self._commands_history[0])
        self.assertEqual(self.commands_ran_count, 1)
