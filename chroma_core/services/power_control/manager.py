# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
import threading
from Queue import Queue

from django.db import transaction

from chroma_core.lib.util import CommandLine, CommandError
from chroma_core.services.log import log_register
from chroma_core.models import PowerControlDevice, PowerControlDeviceOutlet


log = log_register(__name__.split(".")[-1])


class PowerControlManager(CommandLine):
    def __init__(self):
        # Big lock
        self._lock = threading.Lock()
        # Per-device locks
        self._device_locks = defaultdict(threading.Lock)
        self._power_devices = {}
        # Allow us to communicate with our monitoring threads
        self.monitor_task_queue = defaultdict(Queue)

        self._refresh_power_devices()

    def _refresh_power_devices(self):
        # Ensure that we have a fresh view of the DB
        with transaction.commit_manually():
            transaction.commit()

        with self._lock:
            for device in PowerControlDevice.objects.all():
                if device.sockaddr not in self._power_devices:
                    self._power_devices[device.sockaddr] = device

    @property
    def power_devices(self):
        with self._lock:
            return self._power_devices

    def get_monitor_tasks(self, sockaddr):
        with self._lock:
            return self.monitor_task_queue[sockaddr]

    def add_monitor_task(self, sockaddr, task):
        with self._lock:
            self.monitor_task_queue[sockaddr].put(task)

    def register_device(self, device_id):
        device = PowerControlDevice.objects.get(pk=device_id)
        sockaddr = device.sockaddr

        with self._lock:
            self._power_devices[sockaddr] = device

        log.info("Registered device: %s:%s" % sockaddr)

        log.info("Scheduling outlet query for new device: %s:%s" % sockaddr)
        self.add_monitor_task(sockaddr, ("query_device_outlets", {"device_id": device.id}))

    def unregister_device(self, sockaddr):
        sockaddr = tuple(sockaddr)

        with self._lock:
            try:
                del self._power_devices[sockaddr]
                del self._device_locks[sockaddr]
            except KeyError:
                # Never registered with the Manager?
                pass

        log.info("Unregistered device: %s:%s" % sockaddr)

        log.info("Scheduling stop for device monitor: %s:%s" % sockaddr)
        self.add_monitor_task(sockaddr, ("stop", {}))

    def reregister_device(self, device_id):
        # Not happy with this, but we don't have a great way to tell
        # if this was called because some attribute of the PDU was updated
        # or if it was saved due to a relation's update (e.g. an Outlet).
        def _needs_update(old):
            new = PowerControlDevice.objects.get(pk=device_id)

            excludes = ["_state"]
            for k, v in new.__dict__.items():
                if k in excludes:
                    continue
                if getattr(old, k, None) != v:
                    return True
            return False

        for sockaddr, old in self._power_devices.items():
            if old.pk == device_id and _needs_update(old):
                self.unregister_device(sockaddr)
                self.register_device(device_id)
                return
            elif old.pk == device_id:
                log.debug("%s:%s was not updated, no need to reregister" % sockaddr)
                return

        raise RuntimeError("Attempt to re-register unregistered device: %s" % device_id)

    def check_bmc_availability(self, device):
        if not device.is_ipmi:
            raise RuntimeError("Can't check BMC status on non-IPMI device: %s" % device)

        if not device.all_outlets_known:
            log.info("Scheduling query on %s:%s to resolve unknown outlet states." % device.sockaddr)
            self.add_monitor_task(device.sockaddr, ("query_device_outlets", {"device_id": device.id}))

        with self._device_locks[device.sockaddr]:
            bmc_states = {}
            for outlet in device.outlets.all():
                rc, out, err = self.shell(device.monitor_command(outlet.identifier))
                if rc == 0:
                    bmc_states[outlet] = True
                else:
                    log.error("BMC %s did not respond to monitor: %s %s" % (outlet.identifier, out, err))
                    bmc_states[outlet] = False

            return bmc_states

    def check_device_availability(self, device):
        if device.is_ipmi:
            raise RuntimeError("Can't check PDU status on IPMI device: %s" % device)

        if not device.all_outlets_known:
            log.info("Scheduling query on %s:%s to resolve unknown outlet states." % device.sockaddr)
            self.add_monitor_task(device.sockaddr, ("query_device_outlets", {"device_id": device.id}))

        with self._device_locks[device.sockaddr]:
            try:
                self.try_shell(device.monitor_command())
            except CommandError as e:
                log.error("Device %s did not respond to monitor: %s" % (device, e))
                return False
            return True

    @transaction.commit_on_success
    def toggle_device_outlets(self, toggle_state, outlet_ids):
        state_commands = {"on": "poweron_command", "off": "poweroff_command", "reboot": "powercycle_command"}

        for outlet_id in outlet_ids:
            outlet = PowerControlDeviceOutlet.objects.select_related("device").get(pk=outlet_id)
            device = outlet.device
            command = getattr(device, state_commands[toggle_state])

            with self._device_locks[device.sockaddr]:
                try:
                    stdout = self.try_shell(command(outlet.identifier))[1]
                    log.info("Toggled %s:%s -> %s: %s" % (device, outlet.identifier, toggle_state, stdout))
                    has_power = toggle_state in ("on", "reboot")
                except CommandError as e:
                    log.error("Failed to toggle %s:%s -> %s: %s" % (device, outlet.identifier, toggle_state, e.stderr))
                    has_power = None
                PowerControlDeviceOutlet.objects.filter(id=outlet.id).update(has_power=has_power)

    @transaction.commit_on_success
    def query_device_outlets(self, device_id):
        device = PowerControlDevice.objects.select_related().get(pk=device_id)

        # With HYD-2089 landed, we can query PDU outlet states in one
        # shot, rather than sequentially.
        #
        # IPMI is another story. We're landing rudimentary support for
        # IPMI with HYD-2099, but longer-term we will probably want to
        # improve query performance with some kind of fanout.
        with self._device_locks[device.sockaddr]:
            if device.is_ipmi:
                # IPMI -- query sequentially
                for outlet in device.outlets.order_by("identifier"):
                    rc, stdout, stderr = self.shell(device.outlet_query_command(outlet.identifier))

                    # These RCs seem to be common across agents.
                    # Verified: fence_apc, fence_wti, fence_xvm
                    has_power = {0: True, 2: False}.get(rc)
                    if has_power is None:
                        log.error(
                            "Unknown outlet state for %s:%s:%s: %s %s %s"
                            % (device.sockaddr + tuple([outlet.identifier, rc, stdout, stderr]))
                        )
                    log.debug("Learned outlet %s on %s:%s" % (tuple([outlet]) + device.sockaddr))
                    PowerControlDeviceOutlet.objects.filter(id=outlet.id).update(has_power=has_power)
            else:
                # PDU -- one-shot query
                rc, stdout, stderr = self.try_shell(device.outlet_list_command())
                for line in stdout.split("\n"):
                    try:
                        id, name, status = line.split(",")
                    except ValueError:
                        # garbage line
                        log.debug("Garbage line in agent stdout: %s" % line)
                        continue

                    try:
                        outlet = [o for o in device.outlets.all() if o.identifier == id][0]
                    except IndexError:
                        log.debug("Skipping unknown outlet %s:%s:%s" % (device.sockaddr + tuple([id])))
                        continue

                    has_power = {"ON": True, "OFF": False}.get(status)
                    if has_power is None:
                        log.error(
                            "Unknown outlet state for %s:%s:%s: %s %s %s"
                            % (device.sockaddr + tuple([id, rc, stdout, stderr]))
                        )

                    log.debug("Learned outlet %s on %s:%s" % (tuple([outlet]) + device.sockaddr))
                    PowerControlDeviceOutlet.objects.filter(id=outlet.id).update(has_power=has_power)
