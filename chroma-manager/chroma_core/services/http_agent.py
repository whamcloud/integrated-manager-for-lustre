#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
import uuid
import Queue
import threading
import datetime
from chroma_core.models import HostContactAlert, ManagedHost, HostRebootEvent

from chroma_core.services.queue import ServiceQueue
from chroma_core.services.rpc import ServiceRpcInterface
from django.core.handlers.wsgi import WSGIHandler
from chroma_core.services import ChromaService, ServiceThread, log_register, _amqp_connection
from chroma_agent_comms.views import MessageView
import gevent.wsgi
from settings import HTTP_AGENT_PORT


log = log_register(__name__)


# TODO: get a firm picture of whether upgrades from 1.0.x will be done -- if so then
# a script is needed to set up an existing SSH-based system with certificates.

# TODO: interesting tests:
# * All permutations of startup order (with some meaningful delay between startups) of service, http_agent, agent
# * Restarting each component in the chain and checking the system recovers to a sensible state
# * The above for each of the different sets of message handling logic on the service side (plugin_runner, job_scheduler, one of lustre/logs)
# * For all services, check they terminate with SIGTERM in a timely manner (including when they are
#   doing something).  Check this in dev mode and in production (init scripts/supervisor) mode.
# * Run through some error-less scenarios and grep the logs for WARN and ERROR
# * Modify some client and server certificates slightly and check they are rejected (i.e.
#   check that we're really verifying the signatures and not just believing certificates)
#
# * remove a host and then try connecting with that host's old certificate
# * For all the calls to security_log, reproduce the situation and check they hit
#
# * check that service stop and start on the agent works
# * check that after adding and removing a host, no chroma-agent or chroma-agent-daemon services are running


# TODO: on the agent side, check that we still have a nice way to get a dump of the#
# device detection JSON output *and* the corresponding outputs from the wrapped commands


class AgentTxQueue(ServiceQueue):
    name = "agent_tx"


class AgentSessionRpc(ServiceRpcInterface):
    methods = ['reset_session', 'remove_host']


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


class Session(object):
    def __init__(self, plugin):
        self.id = uuid.uuid4().__str__()
        self.plugin = plugin


class SessionCollection(object):
    def __init__(self, queues):
        self._sessions = {}
        self._queues = queues

    def remove_host(self, fqdn):
        self._sessions.pop(fqdn, None)

    def get(self, fqdn, plugin, id = None):
        session = self._sessions[(fqdn, plugin)]
        if id is not None and session.id != id:
            raise KeyError
        return session

    def create(self, fqdn, plugin):
        if fqdn in self._sessions:
            log.warning("Destroying session %s/%s/%s to create new one" % (fqdn, self._sessions[fqdn].plugin, self._sessions[fqdn].id))
            # TODO: send a message upstream to notify that the session is over
            pass
        session = Session(plugin)
        self._sessions[(fqdn, plugin)] = session
        return session

    def reset_session(self, fqdn, plugin, session_id):
        if (fqdn, plugin) in self._sessions:
            log.warning("Terminating session on request %s/%s/%s" % (fqdn, plugin, session_id))
            del self._sessions[(fqdn, plugin)]
            self._queues.send(fqdn, {
                'type': 'SESSION_TERMINATE',
                'plugin': plugin,
                'session_id': session_id,
                'session_seq': None,
                'body': None
            })
        else:
            log.warning("Ignoring request to terminate unknown session %s/%s/%s" % (fqdn, plugin, session_id))


class HostQueues(object):
    """Both directions of messages for a single host"""
    def __init__(self, fqdn):
        self.fqdn = fqdn
        self.rx = Queue.Queue()
        self.tx = Queue.Queue()


class HostQueueCollection(object):
    def __init__(self):
        self._host_queues = {}

        # A queue for all plugin RX messages, will be fanned
        # out to an AMQP queue per plugin
        self.plugin_rx_queue = Queue.Queue()

    def get(self, fqdn):
        try:
            return self._host_queues[fqdn]
        except KeyError:
            queues = HostQueues(fqdn)
            self._host_queues[fqdn] = queues
            return queues

    def remove_host(self, fqdn):
        self._host_queues.pop(fqdn, None)

    def send(self, fqdn, message):
        self.get(fqdn).tx.put(message)

    def receive(self, fqdn, message):
        # An extra envelope to record which FQDN sent this message
        self.plugin_rx_queue.put(
            {
                'fqdn': fqdn,
                'session_message': message
            }
        )


class AmqpTxForwarder(object):
    def __init__(self, queue_collection):
        self._queue = AgentTxQueue()
        self._queue_collection = queue_collection

    def on_message(self, message):
        log.debug("AmqpTxForwarder.on_message: %s/%s/%s %s" % (
            message['fqdn'],
            message['session_message']['plugin'],
            message['session_message']['session_id'],
            message['session_message']['type']))
        fqdn = message['fqdn']
        session_message = message['session_message']
        self._queue_collection.send(fqdn, session_message)

    def run(self):
        self._queue.serve(self.on_message)

    def stop(self):
        self._queue.stop()


class AmqpRxForwarder(object):
    def __init__(self, queue_collection):
        self._stopping = threading.Event()
        self._queue_collection = queue_collection

    def run(self):
        with _amqp_connection() as conn:
            while not self._stopping.is_set():
                try:
                    msg = self._queue_collection.plugin_rx_queue.get(block = True, timeout = 1)
                except Queue.Empty:
                    pass
                else:
                    plugin_name = msg['session_message']['plugin']
                    rx_queue_name = "agent_%s_rx" % plugin_name
                    q = conn.SimpleQueue(rx_queue_name, serializer = 'json')
                    q.put(msg)

    def stop(self):
        self._stopping.set()


class Service(ChromaService):
    def reset_session(self, fqdn, plugin, session_id):
        return self.sessions.reset_session(fqdn, plugin, session_id)

    def remove_host(self, fqdn):
        self.sessions.remove_host(fqdn)
        self.queues.remove_host(fqdn)
        self.hosts.remove_host(fqdn)

        # TODO: ensure there are no GETs left in progress after this completes
        # TODO: drain plugin_rx_queue so that anything we will send to AMQP has been sent before this returns

    def __init__(self):
        super(Service, self).__init__()

        self.queues = HostQueueCollection()
        self.sessions = SessionCollection(self.queues)
        self.hosts = HostStateCollection()

    def run(self):
        self.amqp_tx_forwarder = AmqpTxForwarder(self.queues)
        self.amqp_rx_forwarder = AmqpRxForwarder(self.queues)

        # This thread listens to an AMQP queue and appends incoming messages
        # to queues for retransmission to agents
        tx_svc_thread = ServiceThread(self.amqp_tx_forwarder)
        # This thread listens to local queues and appends received messages
        # to an AMQP queue
        rx_svc_thread = ServiceThread(self.amqp_rx_forwarder)
        rx_svc_thread.start()
        tx_svc_thread.start()

        # This thread services session management RPCs, so that other
        # services can explicitly request a session reset
        session_rpc_thread = ServiceThread(AgentSessionRpc(self))
        session_rpc_thread.start()

        # Hook up the request handler
        MessageView.queues = self.queues
        MessageView.sessions = self.sessions
        MessageView.hosts = self.hosts

        # The thread for generating HostOfflineAlerts
        host_checker_thread = ServiceThread(HostContactChecker(self.hosts))
        host_checker_thread.start()

        # The main thread serves incoming requests to exchanges messages
        # with agents, until it is interrupted (gevent handles signals for us)
        self.server = gevent.wsgi.WSGIServer(('', HTTP_AGENT_PORT), WSGIHandler())
        self.server.serve_forever()

        session_rpc_thread.stop()
        tx_svc_thread.stop()
        rx_svc_thread.stop()
        host_checker_thread.stop()
        session_rpc_thread.join()
        tx_svc_thread.join()
        tx_svc_thread.join()
        host_checker_thread.join()

    def stop(self):
        self.server.stop()
