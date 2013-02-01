#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
import uuid
from chroma_core.services import log_register
from chroma_core.services.rpc import ServiceRpcInterface


log = log_register(__name__)


class AgentSessionRpc(ServiceRpcInterface):
    methods = ['reset_session', 'remove_host']


class SessionCollection(object):
    def __init__(self, queues):
        self._lock = threading.Lock()
        self._sessions = {}
        self._queues = queues

    def remove_host(self, fqdn):
        with self._lock:
            self._sessions.pop(fqdn, None)

    def get(self, fqdn, plugin, id = None):
        with self._lock:
            session = self._sessions[(fqdn, plugin)]
            if id is not None and session.id != id:
                raise KeyError
            return session

    def create(self, fqdn, plugin):
        with self._lock:
            if (fqdn, plugin) in self._sessions:
                old_session = self._sessions[(fqdn, plugin)]
                log.warning("Destroying session %s/%s/%s to create new one" % (fqdn, plugin, old_session.id))
                # Send a message upstream to notify that the previous session is over
                self._queues.receive({
                    'fqdn': fqdn,
                    'type': 'SESSION_TERMINATE',
                    'plugin': plugin,
                    'session_id': old_session.id,
                    'session_seq': None,
                    'body': None
                })

            session = Session(plugin)
            self._sessions[(fqdn, plugin)] = session
            # Send a message upstream to notify that the previous session is over
            self._queues.receive({
                'fqdn': fqdn,
                'type': 'SESSION_CREATE',
                'plugin': plugin,
                'session_id': session.id,
                'session_seq': None,
                'body': None
            })
            return session

    def reset_session(self, fqdn, plugin, session_id):
        """
        This is a reset in the TX direction, to tell the agent that a session has gone away
        """
        with self._lock:
            if (fqdn, plugin) in self._sessions:
                log.warning("Terminating session on request %s/%s/%s" % (fqdn, plugin, session_id))
                del self._sessions[(fqdn, plugin)]
                self._queues.send({
                    'fqdn': fqdn,
                    'type': 'SESSION_TERMINATE',
                    'plugin': plugin,
                    'session_id': session_id,
                    'session_seq': None,
                    'body': None
                })
            else:
                log.warning("Ignoring request to terminate unknown session %s/%s/%s" % (fqdn, plugin, session_id))

    def reset_fqdn_sessions(self, victim_fqdn):
        """
        This is a reset in the RX direction, to tell services that an agent session has gone away
        """
        with self._lock:
            remove_keys = []
            for (fqdn, plugin), session in self._sessions.items():
                if fqdn == victim_fqdn:
                    log.info("Terminating session %s/%s/%s" % (fqdn, plugin, session.id))
                    self._queues.receive({
                        'fqdn': fqdn,
                        'type': 'SESSION_TERMINATE',
                        'plugin': plugin,
                        'session_id': session.id,
                        'session_seq': None,
                        'body': None
                    })
                    remove_keys.append((fqdn, plugin))

            for key in remove_keys:
                del self._sessions[key]

            log.debug("Session count: %s" % len(self._sessions))


class Session(object):
    def __init__(self, plugin):
        self.id = uuid.uuid4().__str__()
        self.plugin = plugin
