# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import logging
import threading
import datetime

from chroma_agent_comms.views import MessageView
from chroma_core.models.host import ManagedHost
from chroma_core.models import HostContactAlert, HostRebootEvent
from chroma_core.services import log_register
from chroma_core.services.job_scheduler import job_scheduler_notify
from iml_common.lib.date_time import IMLDateTime

log = log_register("http_agent_host_state")


class HostState(object):
    """
    The http_agent service maintains some per-host state unrelated to
    managing communication sessions, in order to detect and report
    reboots and generate timeouts.
    """

    # We get an update at the start of every long poll
    CONTACT_TIMEOUT = MessageView.LONG_POLL_TIMEOUT * 2

    def __init__(self, fqdn, boot_time, client_start_time):
        self.last_contact = None
        self.fqdn = fqdn
        self._healthy = False
        self._host = ManagedHost.objects.get(fqdn=self.fqdn)

        self._last_contact = IMLDateTime.utcnow()
        self._boot_time = boot_time
        self._client_start_time = client_start_time

    def update_health(self, healthy):
        HostContactAlert.notify(self._host, not healthy)
        self._healthy = healthy

    def update(self, boot_time, client_start_time):
        """
        :return A boolean, true if the agent should be sent a SESSION_TERMINATE_ALL: indicates
                whether a fresh client run (different start time) is seen.
        """
        self.last_contact = IMLDateTime.utcnow()
        if boot_time is not None and boot_time != self._boot_time:
            if self._boot_time is not None:
                HostRebootEvent.register_event(alert_item=self._host, boot_time=boot_time, severity=logging.WARNING)
                log.warning("Server %s rebooted at %s" % (self.fqdn, boot_time))
            self._boot_time = boot_time
            job_scheduler_notify.notify(self._host, self._boot_time, {"boot_time": boot_time})

        require_reset = False
        if client_start_time is not None and client_start_time != self._client_start_time:
            if self._client_start_time is not None:
                log.warning("Agent restart on server %s at %s" % (self.fqdn, client_start_time))
            require_reset = True

            self._client_start_time = client_start_time

        if not self._healthy:
            self.update_health(True)

        return require_reset

    def poll(self):
        if self._healthy:
            time_since_contact = IMLDateTime.utcnow() - self.last_contact
            if time_since_contact > datetime.timedelta(seconds=self.CONTACT_TIMEOUT):
                self.update_health(False)
        return self._healthy


class HostStateCollection(object):
    """
    Store some per-host state, things we will check and update
    without polling/continuously updating the database.
    """

    def __init__(self):
        self._hosts = {}

        for mh in ManagedHost.objects.all().values("fqdn", "boot_time"):
            self._hosts[mh["fqdn"]] = HostState(mh["fqdn"], mh["boot_time"], None)

    def remove_host(self, fqdn):
        self._hosts.pop(fqdn, None)

    def update(self, fqdn, boot_time=None, client_start_time=None):
        try:
            state = self._hosts[fqdn]
        except KeyError:
            state = self._hosts[fqdn] = HostState(fqdn, None, None)

        return state.update(boot_time, client_start_time)

    def items(self):
        return self._hosts.items()


class HostStatePoller(object):
    """
    This thread periodically calls the .poll method of all the
    hosts in a collection, in order to generate timeouts.
    """

    # How often to wake up and update alerts
    POLL_INTERVAL = 10

    # How long to wait at startup (to avoid immediately generating offline
    # alerts for all hosts when restarting, aka HYD-1273)
    STARTUP_DELAY = 30

    def __init__(self, host_state_collection, sessions):
        self._stopping = threading.Event()
        self._hosts = host_state_collection
        self._sessions = sessions

    def run(self):
        self._stopping.wait(self.STARTUP_DELAY)

        while not self._stopping.is_set():
            for fqdn, host_state in self._hosts.items():
                healthy = host_state.poll()
                if not healthy:
                    self._sessions.reset_fqdn_sessions(host_state.fqdn)

            self._stopping.wait(self.POLL_INTERVAL)

    def stop(self):
        self._stopping.set()
