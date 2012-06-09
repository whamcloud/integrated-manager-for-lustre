#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os
import time
import datetime
import threading
import pickle

from django.db import transaction

from chroma_core.lib.storage_plugin import messaging
from chroma_core.lib.storage_plugin.log import storage_plugin_log
from chroma_core.lib.storage_plugin.messaging import Timeout
from chroma_core.models import AgentSession, ManagedHost, StorageResourceRecord, StorageResourceOffline


# Thread-per-session is just a convenient way of coding this.  The actual required
# behaviour is for a session to always run in the same process.  So we could
# equally use a thread pool for advancing the loop of each session, or we
# could use a multiprocessing pool as long as a session is always advanced
# in the same worker process.
class PluginSession(threading.Thread):
    def __init__(self, root_resource_id, *args, **kwargs):
        self.stopping = False
        self.stopped = False
        self.root_resource_id = root_resource_id
        self.initialized = False

        super(PluginSession, self).__init__(*args, **kwargs)

    def run(self):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        record = StorageResourceRecord.objects.get(id=self.root_resource_id)
        plugin_klass = storage_plugin_manager.get_plugin_class(
                          record.resource_class.storage_plugin.module_name)

        RETRY_DELAY_MIN = 1
        RETRY_DELAY_MAX = 256
        retry_delay = RETRY_DELAY_MIN
        while not self.stopping:
            last_retry = datetime.datetime.now()
            try:
                # Note: get a fresh root_resource each time as the Plugin
                # instance will modify it.
                self._scan_loop(plugin_klass, record)
            except Exception:
                run_duration = datetime.datetime.now() - last_retry
                if last_retry and run_duration > datetime.timedelta(seconds = RETRY_DELAY_MAX):
                    # If the last run was long running (i.e. probably ran okay until something went
                    # wrong) then retry quickly.
                    retry_delay = RETRY_DELAY_MIN
                else:
                    # If we've already retried recently, then start backing off.
                    retry_delay *= 2

                storage_plugin_log.warning("Exception in scan loop for resource %s, waiting %ss before restart" % (self.root_resource_id, retry_delay))
                import sys
                import traceback
                exc_info = sys.exc_info()
                backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
                storage_plugin_log.warning("Backtrace: %s" % backtrace)

                for i in range(0, retry_delay):
                    if self.stopping:
                        break
                    else:
                        time.sleep(1)
            else:
                storage_plugin_log.info("Session %s: out of scan loop cleanly" % self.root_resource_id)

        storage_plugin_log.info("Session %s: Dropped out of retry loop" % self.root_resource_id)
        self.stopped = True

    def _scan_loop(self, plugin_klass, record):
        storage_plugin_log.debug("Session %s: starting scan loop" % self.root_resource_id)
        instance = plugin_klass(self.root_resource_id)
        # TODO: impose timeouts on plugin calls (especially teardown)
        try:
            storage_plugin_log.debug("Session %s: >>initial_scan" % self.root_resource_id)
            instance.do_initial_scan()
            self.initialized = True
            storage_plugin_log.debug("Session %s: <<initial_scan" % self.root_resource_id)
            first_update = True
            while not self.stopping:
                storage_plugin_log.debug("Session %s: >>periodic_update (%s)" % (self.root_resource_id, instance.update_period))
                instance.do_periodic_update()
                if first_update:
                    # NB don't mark something as online until the first update has completed, to avoid
                    # flapping if something has a working initial_scan and a failing update_scan
                    StorageResourceOffline.notify(record, False)
                    first_update = False

                storage_plugin_log.debug("Session %s: <<periodic_update" % self.root_resource_id)

                i = 0
                while i < instance.update_period and not self.stopping:
                    time.sleep(1)
                    i = i + 1
        except Exception:
            raise
        finally:
            StorageResourceOffline.notify(record, True)
            self.initialized = False
            instance.do_teardown()

    def stop(self):
        self.stopping = True


class DaemonRpc(object):
    def __init__(self, wrapped = None):
        self._stopping = False
        self.wrapped = wrapped

        if wrapped:
            # Raise an exception if any of the declared methods don't exist
            # on the wrapped object
            for method in self.methods:
                getattr(wrapped, method)

    def __getattr__(self, name):
        if name in self.methods:
            return lambda *args, **kwargs: self.__class__._call(name, *args, **kwargs)
        else:
            raise AttributeError(name)

    @classmethod
    def _call(cls, fn_name, *args, **kwargs):
        storage_plugin_log.info("Started rpc '%s'" % fn_name)
        queue_name = cls.__name__
        result = messaging.rpc(queue_name, {
            'method': fn_name,
            'args': args,
            'kwargs': kwargs})

        if 'exception' in result:
            exception = pickle.loads(str(result['exception']))
            storage_plugin_log.error("DaemonRpc._call: exception: %s" % result['backtrace'])
            raise exception

        storage_plugin_log.info("Completed rpc '%s' (result=%s)" % (fn_name, result))

    def _local_call(self, fn_name, *args, **kwargs):
        storage_plugin_log.debug("_local_call: %s" % fn_name)
        assert (fn_name in self.methods)
        fn = getattr(self.wrapped, fn_name)
        return fn(*args, **kwargs)

    def main_loop(self):
        queue_name = self.__class__.__name__
        from chroma_core.lib.storage_plugin.messaging import PluginRequest, PluginResponse

        def handler(body):
            storage_plugin_log.info("DaemonRpc %s %s %s %s" % (body['id'], body['method'], body['args'], body['kwargs']))
            request_id = body['id']
            try:
                result = {'result': self._local_call(body['method'], *body['args'], **body['kwargs'])}
            except Exception, e:
                import sys
                import traceback
                exc_info = sys.exc_info()
                backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
                result = {
                        'exception': pickle.dumps(e),
                        'backtrace': backtrace
                        }
                storage_plugin_log.error("DaemonRpc: exception calling %s" % body['method'])
            PluginResponse.send(queue_name, "", request_id, result)

        # Enter a loop to service requests until self.stopping is set
        storage_plugin_log.info("Starting DaemonRpc main loop (%s)" % queue_name)
        retry_period = 1
        max_retry_period = 60
        while not self._stopping:
            try:
                PluginRequest.handle_all(queue_name, "", handler)
                time.sleep(1)
            except Exception:
                import sys
                import traceback
                exc_info = sys.exc_info()
                backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))

                storage_plugin_log.error("Exception running AMQP consumer: %s" % backtrace)
                storage_plugin_log.error("Retrying in %d seconds" % retry_period)

                i = 0
                while i < retry_period and not self._stopping:
                    time.sleep(1)
                    i += 1
                if retry_period < max_retry_period:
                    retry_period *= 2
        storage_plugin_log.info("Finished DaemonRpc main loop")

    def stop(self):
        self._stopping = True


class AgentDaemonRpc(DaemonRpc):
    methods = ['await_session', 'remove_host_resources']


class ScanDaemonRpc(DaemonRpc):
    methods = ['remove_resource', 'modify_resource']


class AgentSessionState(object):
    def __init__(self):
        self.plugin_instances = {}


class AgentDaemon(object):
    """Sibling of ScanDaemon.  Rather than actively creating sessions
    and spinning of threads, this class handles incoming information from
    the agents and manages sessions in an event-driven way as messages arrive."""
    def __init__(self):
        self._session_state = {}
        self._stopping = False
        self._processing_lock = threading.Lock()
        self._session_blacklist = set()

    def stop(self):
        self._stopping = True

    def main_loop(self):
        # Evict any existing sessions
        messaging.simple_purge('agent')
        AgentSession.objects.all().delete()
        storage_plugin_log.info("AgentDaemon listening")
        while(not self._stopping):
            storage_plugin_log.debug(">>simple_receive")
            message = messaging.simple_receive('agent')
            storage_plugin_log.debug("<<simple_receive")
            if message:
                with self._processing_lock:
                    storage_plugin_log.debug(">>handle_incoming")
                    self.handle_incoming(message)
                    storage_plugin_log.debug("<<handle_incoming")
            else:
                time.sleep(1)

    def remove_host_resources(self, host_id):
        storage_plugin_log.info("AgentDaemon: removing resources for host %s" % host_id)

        # Stop the session, and block it from starting again
        with self._processing_lock:
            try:
                del self._session_state[host_id]
            except KeyError:
                storage_plugin_log.warning("remove_host_resources: No sessions for host %s" % host_id)
            self._session_blacklist.add(host_id)

        from chroma_core.lib.storage_plugin.query import ResourceQuery
        from chroma_core.lib.storage_plugin.resource_manager import resource_manager
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        for plugin_name in storage_plugin_manager.loaded_plugins.keys():
            try:
                record = ResourceQuery().get_record_by_attributes('linux', 'PluginAgentResources',
                        host_id = host_id, plugin_name = plugin_name)
            except StorageResourceRecord.DoesNotExist:
                pass
            else:
                resource_manager.global_remove_resource(record.id)

        storage_plugin_log.info("AgentDaemon: finished removing resources for host %s" % host_id)

    def await_session(self, host_id):
        started = False
        timeout = 30
        start_time = datetime.datetime.now()
        storage_plugin_log.debug("AgentDaemon: starting await_session")
        while not started:
            started = host_id in self._session_state
            if not started:
                time.sleep(1)

            if datetime.datetime.now() - start_time > datetime.timedelta(seconds = timeout):
                raise Timeout("Timed out after %s seconds waiting for session to start")
        storage_plugin_log.debug("AgentDaemon: finished await_session")

    @transaction.commit_on_success
    def handle_incoming(self, message):
        host_id = message['host_id']
        session_id = message['session_id']
        updates = message['updates']

        if host_id in self._session_blacklist:
            storage_plugin_log.info("Dropping message from blacklisted host %s (undergoing removal)" % host_id)
            return

        try:
            host = ManagedHost.objects.get(id = host_id)
        except ManagedHost.DoesNotExist:
            storage_plugin_log.error("Received agent message for non-existent host %s" % host_id)
            return

        storage_plugin_log.debug("Received agent message for %s" % host)

        try:
            session = AgentSession.objects.get(host = host, session_id = session_id)
        except AgentSession.DoesNotExist:
            storage_plugin_log.error("Received agent message for non-existent session %s" % session_id)
            return

        try:
            host_state = self._session_state[host.id]
            if len(host_state) and set(host_state.keys()) != set([session_id]):
                # An old session is in the state for this host, flush it out
                storage_plugin_log.info("Old sessions %s for host %s, removing" % (set(host_state.keys()), host))
                raise KeyError
                # TODO: tear down plugin instances (or document that there is no teardown for agent plugins)

        except KeyError:
            host_state = {}
            self._session_state[host.id] = host_state

        try:
            session_state = host_state[session.session_id]
            initial = False
        except KeyError:
            session_state = AgentSessionState()
            host_state[session.session_id] = session_state
            initial = True

        # TODO: validate plugin_name
        for plugin_name, plugin_data in updates.items():
            from chroma_core.lib.storage_plugin.manager import storage_plugin_manager, PluginNotFound
            from chroma_core.lib.storage_plugin.query import ResourceQuery
            try:
                record = ResourceQuery().get_record_by_attributes('linux', 'PluginAgentResources',
                        plugin_name = plugin_name, host_id = host.id)
            except StorageResourceRecord.DoesNotExist:
                resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')
                record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'plugin_name': plugin_name, 'host_id': host.id})

            try:
                klass = storage_plugin_manager.get_plugin_class(plugin_name)
            except PluginNotFound:
                storage_plugin_log.warning("Ignoring information from %s for plugin %s, no such plugin found." % (host, plugin_name))
            else:
                if initial:
                    instance = klass(record.id)
                    session_state.plugin_instances[plugin_name] = instance
                else:
                    instance = session_state.plugin_instances[plugin_name]

                try:
                    if initial:
                        storage_plugin_log.info("Started session for %s on %s" % (plugin_name, host))
                        instance.do_agent_session_start(plugin_data)
                    else:
                        instance.do_agent_session_continue(plugin_data)
                except Exception:
                    import sys
                    import traceback
                    exc_info = sys.exc_info()
                    backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
                    storage_plugin_log.error("Exception in agent session for %s from %s: %s" % (
                        plugin_name, host, backtrace))
                    storage_plugin_log.error("Data: %s" % plugin_data)

                    # Tear down the session as we are no longer coherent, information could have
                    # been lost.
                    session.delete()
                    del self._session_state[host.id]
                    break


class ScanDaemon(object):
    def __init__(self):
        self.stopping = False

        self._session_lock = threading.Lock()

        self._all_sessions = {}
        # Map of module name to map of root_resource_id to PluginSession
        self.plugins = {}
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        for p in storage_plugin_manager.loaded_plugins.keys():
            # Create sessions for all root resources
            sessions = {}
            for srr_id in self.root_resource_ids(p):
                session = PluginSession(srr_id)
                sessions[srr_id] = session
                self._all_sessions[srr_id] = session

            self.plugins[p] = sessions

        session_count = reduce(lambda x, y: x + y, [len(s) for s in self.plugins.values()])
        storage_plugin_log.info("ScanDaemon: Loaded %s plugins, %s sessions" % (len(self.plugins), session_count))

    def modify_resource(self, resource_id, attrs):
        storage_plugin_log.info("ScanDaemon: modifying %s" % resource_id)
        with self._session_lock:
            try:
                kill_session = self._all_sessions[resource_id]
            except KeyError:
                pass
            else:
                kill_session.stop()
                storage_plugin_log.info("ScanDaemon: waiting for session to stop")
                from time import sleep
                while(not kill_session.stopped):
                    sleep(1)
                storage_plugin_log.info("ScanDaemon: stopped.")
                for plugin, sessions in self.plugins.items():
                    if resource_id in sessions:
                        del sessions[resource_id]
                del self._all_sessions[resource_id]

            record = StorageResourceRecord.objects.get(pk = resource_id)
            record.update_attributes(attrs)
            record.save()

        storage_plugin_log.info("ScanDaemon: finished removing %s" % resource_id)

    def remove_resource(self, resource_id):
        # Is there a session to kill?
        storage_plugin_log.info("ScanDaemon: removing %s" % resource_id)
        with self._session_lock:
            try:
                kill_session = self._all_sessions[resource_id]
            except KeyError:
                pass
            else:
                kill_session.stop()
                storage_plugin_log.info("ScanDaemon: waiting for session to stop")
                from time import sleep
                while(not kill_session.stopped):
                    sleep(1)
                storage_plugin_log.info("ScanDaemon: stopped.")

            from chroma_core.lib.storage_plugin.resource_manager import resource_manager
            resource_manager.global_remove_resource(resource_id)
        storage_plugin_log.info("ScanDaemon: finished removing %s" % resource_id)

    def root_resource_ids(self, plugin):
        """Return the PK of all StorageResourceRecords for 'plugin' which have no parents"""
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        # We will be polling, to need to commit to see new data
        with transaction.commit_manually():
            transaction.commit()
            ids = storage_plugin_manager.get_scannable_resource_ids(plugin)
            transaction.commit()
        return ids

    def main_loop(self):
        storage_plugin_log.info("ScanDaemon: entering main loop")
        for scannable_id, session in self._all_sessions.items():
            session.start()

        while not self.stopping:
            time.sleep(5)

            # Look for any new root resources and start sessions for them
            with self._session_lock:
                for plugin, sessions in self.plugins.items():
                    for rrid in self.root_resource_ids(plugin):
                        if not rrid in sessions:
                            storage_plugin_log.info("ScanDaemon: new session for resource %s" % rrid)
                            s = PluginSession(rrid)
                            sessions[rrid] = s
                            self._all_sessions[rrid] = s
                            s.start()

        storage_plugin_log.info("ScanDaemon: leaving main loop")

        self._stop_sessions()

    def _stop_sessions(self):
        JOIN_TIMEOUT = 5

        storage_plugin_log.info("ScanDaemon: stopping sessions")
        for scannable_id, session in self._all_sessions.items():
            session.stop()
        storage_plugin_log.info("ScanDaemon: joining sessions")
        for scannable_id, session in self._all_sessions.items():
            session.join(timeout = JOIN_TIMEOUT)
            if session.isAlive():
                storage_plugin_log.warning("ScanDaemon: session failed to return in %s seconds, forcing exit" % JOIN_TIMEOUT)
                os._exit(-1)

    def stop(self):
        self.stopping = True
