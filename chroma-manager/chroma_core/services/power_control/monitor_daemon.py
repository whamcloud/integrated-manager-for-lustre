#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
from Queue import Empty

from chroma_core.services.log import log_register
from chroma_core.models import PowerControlDeviceUnavailableAlert


log = log_register(__name__.split('.')[-1])


class PowerDeviceMonitor(threading.Thread):
    def __init__(self, device, power_control_manager):
        super(PowerDeviceMonitor, self).__init__()
        self.device = device
        self._manager = power_control_manager
        self._stopping = threading.Event()

    def run(self):
        log.info("Starting monitor for %s" % self.device)

        while not self._stopping.is_set():
            available = self._manager.check_device_availability(self.device)
            PowerControlDeviceUnavailableAlert.notify(self.device,
                                                      not available)
            log.debug("Checked on %s:%s: %s" % (self.device.sockaddr + tuple(["available" if available else "unavailable"])))
            self._stopping.wait(timeout = 10)

    def stop(self):
        log.info("Stopping monitor for %s" % self.device)
        self._stopping.set()


class PowerMonitorDaemon(object):
    def __init__(self, power_control_manager):
        self._manager = power_control_manager
        self._stopping = threading.Event()

        self.device_monitors = {}

        for sockaddr, device in self._manager.power_devices.items():
            self.device_monitors[sockaddr] = PowerDeviceMonitor(device,
                                                                self._manager)

        log.info("Found %d power devices to monitor" % len(self.device_monitors))

    def run(self):
        log.info("entering main loop")

        for monitor in self.device_monitors.values():
            monitor.start()

        while not self._stopping.is_set():
            try:
                devices_to_reregister = self._manager.reregister_queue.get_nowait()
            except Empty:
                devices_to_reregister = []

            # Check for new devices to monitor
            for sockaddr, device in self._manager.power_devices.items():
                if not sockaddr in self.device_monitors:
                    log.info("Found new power device: %s:%s" % sockaddr)
                    self.device_monitors[sockaddr] = PowerDeviceMonitor(device,
                                                                self._manager)
                    self.device_monitors[sockaddr].start()

            # Check for old devices to stop monitoring
            for sockaddr, monitor in self.device_monitors.items():
                if (sockaddr not in self._manager.power_devices
                    or sockaddr in devices_to_reregister):
                    log.info("Reaping monitor for old power device: %s:%s" % sockaddr)
                    monitor.stop()
                    monitor.join()
                    del self.device_monitors[sockaddr]

            self._stopping.wait(timeout = 10)

        for monitor in self.device_monitors.values():
            monitor.stop()

        log.info("leaving main loop")

    def stop(self):
        log.info("Stopping...")
        self._stopping.set()

    def join(self):
        log.info("Joining...")
        for monitor in self.device_monitors.values():
            monitor.join()
