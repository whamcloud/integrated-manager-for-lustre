#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import sys
import traceback
import threading
from chroma_core.services.http_agent import AgentSessionRpc
from chroma_core.services.queue import AgentRxQueue

from django.db import transaction
from chroma_core.services.log import log_register
from chroma_core.models import StorageResourceRecord, ManagedHost
from chroma_core.lib.storage_plugin.query import ResourceQuery


log = log_register(__name__.split('.')[-1])


class Session(object):
    def __init__(self, id, instance):
        self.plugin = instance
        self.id = id
        self.seq = 0


class AgentPluginHandler(object):
    """Handle messages sent from the agent.

    Similar to ScanDaemon, the main difference is that ScanDaemon polls plugin callbacks,
    whereas AgentDaemon is driven by a message queue.

    Plugins might be loaded by both AgentDaemon and ScanDaemon, where the ScanDaemon side
    is connecting out to storage controllers, while the AgentDaemon side is getting notifications
    of devices popping up on Lustre servers.

    Creates one plugin instance per plugin per host which sends messages for that plugin.

    """
    def __init__(self, resource_manager, plugin_name):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        self._resource_manager = resource_manager

        # Map of host ID to Session
        self._sessions = {}

        self._stopping = False
        self._processing_lock = threading.Lock()
        self._plugin_name = plugin_name
        self._plugin_klass = storage_plugin_manager.get_plugin_class(plugin_name)

        class PluginQueue(AgentRxQueue):
            plugin = plugin_name

        self._queue = PluginQueue()

    def stop(self):
        self._queue.stop()

    def run(self):
        # Disregard any old messages
        self._queue.purge()
        self._queue.serve(session_callback = self.on_message)

    def remove_host_resources(self, host_id):
        log.info("Removing resources for host %s, plugin %s" % (host_id, self._plugin_name))

        # Stop the session, and block it from starting again
        with self._processing_lock:
            try:
                del self._sessions[host_id]
            except KeyError:
                log.warning("remove_host_resources: No session for host %s" % host_id)

        try:
            record = ResourceQuery().get_record_by_attributes('linux', 'PluginAgentResources',
                    host_id = host_id, plugin_name = self._plugin_name)
        except StorageResourceRecord.DoesNotExist:
            pass
        else:
            self._resource_manager.global_remove_resource(record.id)

        log.info("AgentDaemon: finished removing resources for host %s" % host_id)

    @transaction.commit_on_success
    def setup_host(self, host_id, data):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        with self._processing_lock:
            host = ManagedHost.objects.get(id = host_id)

            try:
                record = ResourceQuery().get_record_by_attributes('linux', 'PluginAgentResources',
                    plugin_name = self._plugin_name, host_id = host.id)
            except StorageResourceRecord.DoesNotExist:
                log.info("Set up plugin %s on host %s" % (self._plugin_name, host))
                resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')
                record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'plugin_name': self._plugin_name, 'host_id': host.id})

            if data is not None:
                instance = self._plugin_klass(self._resource_manager, record.id)
                instance.do_agent_session_start(data)

    def _create_plugin_instance(self, host):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')
        # FIXME: it is weird that the PluginAgentResources class lives in the linux plugin but
        # is used by all of them
        record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'plugin_name': self._plugin_name, 'host_id': host.id})

        return self._plugin_klass(self._resource_manager, record.id)

    @transaction.commit_on_success
    def on_message(self, message):
        with self._processing_lock:
            fqdn = message['fqdn']
            assert message['plugin'] == self._plugin_name

            if message['type'] != 'DATA':
                # We are session aware in that we check sequence numbers etc, but
                # we don't actually require any actions on SESSION_CREATE or
                # SESSION_TERMINATE.
                assert message['type'] in ('SESSION_CREATE', 'SESSION_TERMINATE')
                return

            try:
                host = ManagedHost.objects.get(fqdn = fqdn)
            except ManagedHost.DoesNotExist:
                log.error("Received agent message for non-existent host %s" % fqdn)
                return

            log.debug("Received agent message for %s/%s/%s" % (fqdn, message['plugin'], message['session_id']))

            existing_session = self._sessions.get(host.id, None)
            if existing_session is None:
                if message['session_seq'] == 0:
                    # No existing session, start a new one
                    log.info("New session")
                    self._sessions[host.id] = Session(message['session_id'], self._create_plugin_instance(host))
                else:
                    # Partway through a session, reset it
                    log.info("Nonzero counter for new (to me) session, resetting")
                    AgentSessionRpc().reset_session(fqdn, self._plugin_name, message['session_id'])
                    return

            elif existing_session.id != message['session_id']:
                if message['session_seq'] == 0:
                    # Existing session to be replaced with this one
                    log.info("Replacing session %s/%s with %s/%s" % (
                        self._plugin_name, existing_session.id, self._plugin_name, message['session_id']))
                    self._sessions[host.id] = Session(message['session_id'], self._create_plugin_instance(host))
                else:
                    # Existing session is dead, new session is not at zero, must send a reset
                    log.info("Nonzero counter for new (to me) replacement session, resetting")
                    del self._sessions[host.id]
                    AgentSessionRpc().reset_session(fqdn, self._plugin_name, message['session_id'])
                    return
            else:
                if message['session_seq'] == existing_session.seq + 1:
                    # Continuation of session
                    pass
                else:
                    # Got out of sequence, reset it
                    log.info("Out of sequence message (seq %s, expected %s), resetting" % (message['session_seq'], existing_session.seq + 1))
                    del self._sessions[host.id]
                    AgentSessionRpc().reset_session(fqdn, self._plugin_name, message['session_id'])
                    return

            session = self._sessions.get(host.id, None)
            try:
                if message['session_seq'] == 0:
                    session.plugin.do_agent_session_start(message['body'])
                else:
                    session.seq += 1
                    session.plugin.do_agent_session_continue(message['body'])
            except Exception:
                exc_info = sys.exc_info()
                backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
                log.error("Exception in agent session for %s from %s: %s" % (
                    self._plugin_name, host, backtrace))
                log.error("Data: %s" % message['body'])

                AgentSessionRpc().reset_session(fqdn, self._plugin_name, message['session_id'])
