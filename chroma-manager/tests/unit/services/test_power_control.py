#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
import mock

from django.test import TestCase

from chroma_core.models import PowerControlType, PowerControlDevice
from chroma_core.services.power_control.manager import PowerControlManager
from chroma_core.services.power_control.monitor_daemon import PowerMonitorDaemon

from tests.integration.core.constants import TEST_TIMEOUT


class PowerControlTestCase(TestCase):
    def setUp(self):
        super(PowerControlTestCase, self).setUp()

        PowerControlManager.check_device_availability = mock.Mock()

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

        self.fence_type = PowerControlType.objects.create(agent = 'fake_agent',
                                                          default_username = 'fake',
                                                          default_password = 'fake')

    def tearDown(self):
        self.md_thread.stop()
        self.md_thread.join()
        super(PowerControlTestCase, self).tearDown()

        stray_threads = [name for name in self.thread_class_names if name != "_MainThread"]
        assert len(stray_threads) == 0, "Stray threads after test: %s" % stray_threads

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


@mock.patch('chroma_core.services.power_control.rpc.PowerControlRpc')
class PowerMonitoringTests(PowerControlTestCase):
    def test_monitoring_daemon_starts(self, mocked):
        self.assertIn('MonitorDaemonThread', self.thread_class_names)

    def test_monitoring_daemon_stops(self, mocked):
        self.md_thread.stop()
        self.wait_for_assert(lambda: self.assertNotIn('MonitorDaemonThread', self.thread_class_names))

    def test_pdu_add_remove_spawns_reaps_monitors(self, mocked):
        self.assertNotIn('PowerDeviceMonitor', self.thread_class_names)

        pdu = PowerControlDevice.objects.create(device_type = self.fence_type,
                                                address = 'localhost')
        # This normally happens via a post_save signal
        self.power_manager.register_device(pdu.id)
        self.wait_for_assert(lambda: self.assertIn('PowerDeviceMonitor', self.thread_class_names))

        pdu.mark_deleted()
        # This normally happens via a post_delete signal
        self.power_manager.unregister_device(pdu.sockaddr)
        self.wait_for_assert(lambda: self.assertNotIn('PowerDeviceMonitor', self.thread_class_names))

    def test_pdu_update_respawns_monitors(self, mocked):
        pdu = PowerControlDevice.objects.create(device_type = self.fence_type,
                                                address = 'localhost')
        # This normally happens via a post_save signal
        self.power_manager.register_device(pdu.id)
        self.wait_for_assert(lambda: self.assertIn('PowerDeviceMonitor', self.thread_class_names))

        start_threads = threading.enumerate()
        pdu.address = '1.2.3.4'
        pdu.username = 'bob'
        pdu.save()
        # This normally happens via a post_save signal
        self.power_manager.reregister_device(pdu.id)

        self.wait_for_assert(lambda: self.assertNotEqual(start_threads, threading.enumerate()))
