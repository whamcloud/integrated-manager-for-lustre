#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime
import logging
import threading
from chroma_core.models import ManagedHost, HostContactAlert, HostRebootEvent
from chroma_core.services import log_register

log = log_register("http_agent_host_state")


class HostState(object):
    CONTACT_TIMEOUT = 30

    def __init__(self, fqdn, boot_time, client_start_time):
        self.last_contact = None
        self.fqdn = fqdn
        self._healthy = False
        self._host = ManagedHost.objects.get(fqdn = self.fqdn)

        self._last_contact = datetime.datetime.utcnow()
        self._boot_time = boot_time
        self._client_start_time = client_start_time

    def update_health(self, healthy):
        # TODO: when going into the state, send a message on agent_rx to
        # tell all consumers that the sessions are over... this is annoying
        # because it means that you have to stay in contact the whole time
        # during a long running operation, but the alternative is to have
        # the job_scheduler wait indefinitely for a host that may never
        # come back
        HostContactAlert.notify(self._host, not healthy)
        self._healthy = healthy

    def update(self, boot_time, client_start_time):
        """
        :return A boolean, true if the agent should be sent a SESSION_TERMINATE_ALL: indicates
                whether a fresh client run (different start time) is seen.
        """
        self.last_contact = datetime.datetime.utcnow()
        if boot_time is not None and boot_time != self._boot_time:
            self._boot_time = boot_time
            ManagedHost.objects.filter(fqdn = self.fqdn).update(boot_time = boot_time)
            if self._boot_time is not None:
                HostRebootEvent.objects.create(
                    host = self._host,
                    boot_time = boot_time,
                    severity = logging.WARNING)
                log.warning("Server %s rebooted at %s" % (self.fqdn, boot_time))
                pass

        require_reset = False
        if client_start_time is not None and client_start_time != self._client_start_time:
            self._client_start_time = client_start_time
            if self._client_start_time is not None:
                log.warning("Agent restart on server %s at %s" % (self.fqdn, client_start_time))
            require_reset = True

        if not self._healthy:
            self.update_health(True)

        return require_reset

    def poll(self):
        if self._healthy:
            time_since_contact = datetime.datetime.utcnow() - self.last_contact
            if time_since_contact > datetime.timedelta(seconds = self.CONTACT_TIMEOUT):
                self.update_health(False)


class HostStateCollection(object):
    """
    Store some per-host state, things we will check and update
    without polling/continuously updating the database.
    """
    def __init__(self):
        self._hosts = {}

        for mh in ManagedHost.objects.all().values('fqdn', 'boot_time'):
            self._hosts[mh['fqdn']] = HostState(mh['fqdn'], mh['boot_time'], None)

    def remove_host(self, fqdn):
        self._hosts.pop(fqdn, None)

    def update(self, fqdn, boot_time = None, client_start_time = None):
        try:
            state = self._hosts[fqdn]
        except KeyError:
            state = self._hosts[fqdn] = HostState(fqdn, None, None)

        return state.update(boot_time, client_start_time)

    def items(self):
        return self._hosts.items()


class HostContactChecker(object):
    """
    This thread periodically checks when each host last sent
    us an update, and raises HostOfflineAlert instances
    if a timeout is exceeded.
    """
    def __init__(self, host_state_collection):
        self._stopping = threading.Event()
        self._hosts = host_state_collection

    def run(self):
        # How often to wake up and update alerts
        POLL_INTERVAL = 10

        # How long to wait at startup (to avoid immediately generating offline
        # alerts for all hosts when restarting, aka HYD-1273)
        STARTUP_DELAY = 30

        # How long does a host have to be out of contact before we raise
        # an offline alert for it?

        self._stopping.wait(STARTUP_DELAY)

        while not self._stopping.is_set():
            for fqdn, host_state in self._hosts.items():
                host_state.poll()

            self._stopping.wait(POLL_INTERVAL)

    def stop(self):
        self._stopping.set()
