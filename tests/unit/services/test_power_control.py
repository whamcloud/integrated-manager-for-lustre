import threading

import mock

from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase
from chroma_core.models.power_control import PowerControlType, PowerControlDevice, PowerControlDeviceOutlet
from chroma_core.services.power_control.manager import PowerControlManager
from chroma_core.services.power_control.monitor_daemon import PowerMonitorDaemon, PowerDeviceMonitor
from tests.integration.core.constants import TEST_TIMEOUT


class PowerControlTestCase(IMLUnitTestCase):
    def setUp(self):
        super(PowerControlTestCase, self).setUp()

        PowerControlManager.check_device_availability = mock.Mock()

        self.threads_at_start = set(threading.enumerate())

        self.power_manager = PowerControlManager()
        monitor_daemon = PowerMonitorDaemon(self.power_manager)

        class MonitorDaemonThread(threading.Thread):
            def run(self):
                monitor_daemon.run()

            def stop(self):
                monitor_daemon.stop()
                monitor_daemon.join()

        self.md_thread = MonitorDaemonThread()
        self.md_thread.start()

        self.fence_type = PowerControlType.objects.create(
            agent="fake_agent", default_username="fake", default_password="fake"
        )

    def tearDown(self):
        self.md_thread.stop()
        self.md_thread.join()
        super(PowerControlTestCase, self).tearDown()

        hanging_threads = self.threads_at_start - set(threading.enumerate())

        assert len(hanging_threads) == 0, "Stray threads after test: %s" % hanging_threads

    @property
    def thread_class_names(self):
        return [t.__class__.__name__ for t in threading.enumerate()]

    # TODO: Figure out how to share these things.
    def wait_for_assert(self, lambda_expression, timeout=TEST_TIMEOUT):
        """
        Evaluates lambda_expression once/1s until no AssertionError or hits
        timeout.
        """
        import time
        import inspect

        running_time = 0
        while running_time < timeout:
            try:
                lambda_expression()
            except AssertionError:
                pass
            else:
                break
            time.sleep(1)
            running_time += 1
        self.assertLess(running_time, timeout, "Timed out waiting for %s." % inspect.getsource(lambda_expression))


@mock.patch("chroma_core.services.power_control.rpc.PowerControlRpc")
class PowerMonitoringTests(PowerControlTestCase):
    def test_monitoring_daemon_starts(self, mocked):
        self.assertIn("MonitorDaemonThread", self.thread_class_names)

    def test_monitoring_daemon_stops(self, mocked):
        self.md_thread.stop()
        self.wait_for_assert(lambda: self.assertNotIn("MonitorDaemonThread", self.thread_class_names))

    def test_pdu_add_remove_spawns_reaps_monitors(self, mocked):
        self.assertNotIn("PowerDeviceMonitor", self.thread_class_names)

        pdu = PowerControlDevice.objects.create(device_type=self.fence_type, address="localhost")
        # This normally happens via a post_save signal
        self.power_manager.register_device(pdu.id)
        self.wait_for_assert(lambda: self.assertIn("PowerDeviceMonitor", self.thread_class_names))

        pdu.mark_deleted()
        # This normally happens via a post_delete signal
        self.power_manager.unregister_device(pdu.sockaddr)
        self.wait_for_assert(lambda: self.assertNotIn("PowerDeviceMonitor", self.thread_class_names))

    def test_pdu_update_respawns_monitors(self, mocked):
        pdu = PowerControlDevice.objects.create(device_type=self.fence_type, address="localhost")
        # This normally happens via a post_save signal
        self.power_manager.register_device(pdu.id)
        self.wait_for_assert(lambda: self.assertIn("PowerDeviceMonitor", self.thread_class_names))

        start_threads = threading.enumerate()
        pdu.address = "1.2.3.4"
        pdu.username = "bob"
        pdu.save()
        # This normally happens via a post_save signal
        self.power_manager.reregister_device(pdu.id)

        self.wait_for_assert(lambda: self.assertNotEqual(start_threads, threading.enumerate()))


@mock.patch("chroma_core.services.power_control.rpc.PowerControlRpc")
class MonitorThreadCase(IMLUnitTestCase):
    device_checks_should_fail = False

    def _check_device_availability(self, device):
        return self.device_checks_should_fail

    def _check_bmc_availability(self, device):
        return dict([(o, self.device_checks_should_fail) for o in device.outlets.all()])

    def setUp(self):
        super(MonitorThreadCase, self).setUp()

        patcher = mock.patch.object(PowerControlManager, "check_device_availability", self._check_device_availability)
        patcher.start()

        patcher = mock.patch.object(PowerControlManager, "check_bmc_availability", self._check_bmc_availability)
        patcher.start()

        self.addCleanup(mock.patch.stopall)

    @mock.patch("chroma_core.models.power_control.PowerControlDeviceUnavailableAlert.notify")
    def test_pdu_monitoring(self, mock_notify, mock_rpc):
        # Grab the first non-IPMI type
        type = PowerControlType.objects.filter(max_outlets__gt=0)[0]
        device = PowerControlDevice.objects.create(device_type=type, address="localhost")
        manager = PowerControlManager()
        monitor = PowerDeviceMonitor(device, manager)

        # Check that an OK device notifies OK
        monitor._check_monitored_device()
        mock_notify.assert_called_with(device, True)

        # Check that an unavailable device notifies not OK
        self.device_checks_should_fail = True
        monitor._check_monitored_device()
        mock_notify.assert_called_with(device, False)

    @mock.patch("chroma_core.models.power_control.IpmiBmcUnavailableAlert.notify")
    def test_bmc_monitoring(self, mock_notify, mock_rpc):
        # Grab an IPMI-ish type
        type = PowerControlType.objects.filter(max_outlets=0)[0]
        device = PowerControlDevice.objects.create(device_type=type, address="localhost")
        bmc = PowerControlDeviceOutlet.objects.create(device=device, identifier="localhost")
        manager = PowerControlManager()
        monitor = PowerDeviceMonitor(device, manager)

        # Check that an OK BMC notifies OK
        monitor._check_monitored_device()
        # Note that the notification goes to the BMC (PowerControlDeviceOutlet
        # instance), not the pseudo-PDU device
        mock_notify.assert_called_with(bmc, True)

        # Check that an unavailable BMC notifies not OK
        self.device_checks_should_fail = True
        monitor._check_monitored_device()
        # Note that the notification goes to the BMC (PowerControlDeviceOutlet
        # instance), not the pseudo-PDU device
        mock_notify.assert_called_with(bmc, False)
