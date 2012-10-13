#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from exceptions import KeyError, Exception
import threading
from django.db import transaction
from chroma_core.services.log import log_register
from chroma_core.services.plugin_runner.agent_daemon_interface import AgentDaemonQueue
from chroma_core.models import StorageResourceRecord, ManagedHost, AgentSession
from chroma_core.lib.storage_plugin.query import ResourceQuery


log = log_register(__name__.split('.')[-1])


class AgentSessionState(object):
    def __init__(self):
        self.plugin_instances = {}


class AgentDaemon(object):
    """Handle messages sent from the agent.

    Similar to ScanDaemon, the main difference is that ScanDaemon polls plugin callbacks,
    whereas AgentDaemon is driven by a message queue.

    Plugins might be loaded by both AgentDaemon and ScanDaemon, where the ScanDaemon side
    is connecting out to storage controllers, while the AgentDaemon side is getting notifications
    of devices popping up on Lustre servers.

    Creates one plugin instance per plugin per host which sends messages for that plugin.

    """
    def __init__(self, resource_manager):
        self._resource_manager = resource_manager
        self._session_state = {}
        self._stopping = False
        self._processing_lock = threading.Lock()
        self._session_blacklist = set()
        self._queue = AgentDaemonQueue()

    def stop(self):
        self._queue.stop()

    def run(self):
        # Disregard any old messages
        self._queue.purge()
        # Force new sessions
        AgentSession.objects.all().delete()

        self._queue.serve(self.on_message)

    @transaction.commit_on_success
    def remove_host_resources(self, host_id):
        log.info("Removing resources for host %s" % host_id)

        # Stop the session, and block it from starting again
        with self._processing_lock:
            try:
                del self._session_state[host_id]
            except KeyError:
                log.warning("remove_host_resources: No sessions for host %s" % host_id)
            self._session_blacklist.add(host_id)

        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        for plugin_name in storage_plugin_manager.loaded_plugins.keys():
            try:
                record = ResourceQuery().get_record_by_attributes('linux', 'PluginAgentResources',
                        host_id = host_id, plugin_name = plugin_name)
            except StorageResourceRecord.DoesNotExist:
                pass
            else:
                self._resource_manager.global_remove_resource(record.id)

        log.info("AgentDaemon: finished removing resources for host %s" % host_id)

    @transaction.commit_on_success
    def setup_host(self, host_id, updates):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager, PluginNotFound

        with self._processing_lock:
            host = ManagedHost.objects.get(id = host_id)

            for plugin_name, plugin_data in updates.items():
                try:
                    klass = storage_plugin_manager.get_plugin_class(plugin_name)
                except PluginNotFound:
                    log.warning("Ignoring information from %s for plugin %s, no such plugin found." % (host, plugin_name))
                    continue

                try:
                    record = ResourceQuery().get_record_by_attributes('linux', 'PluginAgentResources',
                        plugin_name = plugin_name, host_id = host.id)
                except StorageResourceRecord.DoesNotExist:
                    log.info("Set up plugin %s on host %s" % (plugin_name, host))
                    resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')
                    record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'plugin_name': plugin_name, 'host_id': host.id})

                instance = klass(self._resource_manager, record.id)
                instance.do_agent_session_start(plugin_data)

    @transaction.commit_on_success
    def on_message(self, message):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager, PluginNotFound

        with self._processing_lock:
            try:
                host_id = message['host_id']
                session_id = message['session_id']
                updates = message['updates']
                #started_at = dateutil.parser.parse(message['started_at'])
                counter = message['counter']
            except KeyError:
                log.error("Malformed message: %s" % message)
                return

            if host_id in self._session_blacklist:
                log.info("Dropping message from blacklisted host %s (undergoing removal)" % host_id)
                return

            try:
                host = ManagedHost.objects.get(id = host_id)
            except ManagedHost.DoesNotExist:
                log.error("Received agent message for non-existent host %s" % host_id)
                return

            log.debug("Received agent message for %s" % host)

            try:
                host_state = self._session_state[host.id]
                if len(host_state) and set(host_state.keys()) != set([session_id]):
                    # An old session is in the state for this host, flush it out
                    log.info("Old sessions %s for host %s, removing" % (set(host_state.keys()), host))
                    raise KeyError
                    # TODO: tear down plugin instances (or document that there is no teardown for agent plugins)
            except KeyError:
                host_state = {}
                self._session_state[host.id] = host_state

            try:
                session_state = host_state[session_id]
                initial = False
            except KeyError:
                if counter == 1:
                    log.debug("Started session (host %s, session ID %s, counter %s)" % (
                        host, session_id, counter))
                    session_state = AgentSessionState()
                    host_state[session_id] = session_state
                    initial = True
                else:
                    log.debug("Dropping message (host %s, session ID %s, counter %s)" % (
                        host, session_id, counter))
                    return

            for plugin_name, plugin_data in updates.items():
                try:
                    klass = storage_plugin_manager.get_plugin_class(plugin_name)
                except PluginNotFound:
                    log.warning("Ignoring information from %s for plugin %s, no such plugin found." % (host, plugin_name))
                    continue

                try:
                    record = ResourceQuery().get_record_by_attributes('linux', 'PluginAgentResources',
                            plugin_name = plugin_name, host_id = host.id)
                except StorageResourceRecord.DoesNotExist:
                    log.info("Start receiving from new plugin '%s'" % plugin_name)
                    resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')
                    record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'plugin_name': plugin_name, 'host_id': host.id})

                if initial:
                    instance = klass(self._resource_manager, record.id)
                    session_state.plugin_instances[plugin_name] = instance
                else:
                    instance = session_state.plugin_instances[plugin_name]

                try:
                    if initial:
                        log.info("Started session for %s on %s" % (plugin_name, host))
                        instance.do_agent_session_start(plugin_data)
                    else:
                        instance.do_agent_session_continue(plugin_data)
                except Exception:
                    import sys
                    import traceback
                    exc_info = sys.exc_info()
                    backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
                    log.error("Exception in agent session for %s from %s: %s" % (
                        plugin_name, host, backtrace))
                    log.error("Data: %s" % plugin_data)

                    # Tear down the session
                    del self._session_state[host.id]
                    # TODO: signal http_agent service to restart session
                    break
