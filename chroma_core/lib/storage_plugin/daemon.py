
import os
import time
import datetime
import threading
import pickle

from django.db import transaction

from chroma_core.lib.storage_plugin.log import storage_plugin_log
from chroma_core.lib.storage_plugin.messaging import Timeout


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
        from chroma_core.lib.storage_plugin.query import ResourceQuery
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        from chroma_core.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(id=self.root_resource_id)
        plugin_klass = storage_plugin_manager.get_plugin_class(
                          record.resource_class.storage_plugin.module_name)
        root_resource = ResourceQuery().get_resource(record)

        RETRY_DELAY_MIN = 1
        RETRY_DELAY_MAX = 256
        retry_delay = RETRY_DELAY_MIN
        while not self.stopping:
            last_retry = datetime.datetime.now()
            try:
                self._scan_loop(plugin_klass, root_resource)
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

    def _scan_loop(self, plugin_klass, root_resource):
        storage_plugin_log.debug("Session %s: starting scan loop" % root_resource._handle)
        instance = plugin_klass(self.root_resource_id)
        # TODO: impose timeouts on plugin calls (especially teardown)
        try:
            storage_plugin_log.debug("Session %s: >>initial_scan" % root_resource._handle)
            instance.do_initial_scan(root_resource)
            self.initialized = True
            storage_plugin_log.debug("Session %s: <<initial_scan" % root_resource._handle)
            while not self.stopping:
                storage_plugin_log.debug("Session %s: >>periodic_update" % root_resource._handle)
                instance.do_periodic_update(root_resource)
                storage_plugin_log.debug("Session %s: <<periodic_update" % root_resource._handle)

                i = 0
                while i < instance.update_period and not self.stopping:
                    time.sleep(1)
        except Exception:
            raise
        finally:
            self.initialized = False
            instance.do_teardown()

    def stop(self):
        self.stopping = True


class DaemonRpc(object):
    methods = ['remove_resource', 'start_session']

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
            return lambda *args, **kwargs: DaemonRpc._call(name, *args, **kwargs)
        else:
            raise AttributeError(name)

    @classmethod
    def _call(cls, fn_name, *args, **kwargs):
        from chroma_core.lib.storage_plugin.messaging import control_rpc
        storage_plugin_log.info("Started rpc '%s'" % fn_name)
        result = control_rpc({
            'method': fn_name,
            'args': args,
            'kwargs': kwargs})

        if isinstance(result, str):
            exception = pickle.loads(str)
            raise exception

        storage_plugin_log.info("Completed rpc '%s' (result=%s)" % (fn_name, result))

    def _local_call(self, fn_name, *args, **kwargs):
        assert (fn_name in self.methods)
        fn = getattr(self.wrapped, fn_name)
        return fn(*args, **kwargs)

    def main_loop(self):
        from chroma_core.lib.storage_plugin.messaging import PluginRequest, PluginResponse

        # Declare the action that we will perform for each request
        plugin_name, resource_tag = ("_control", "daemon")

        def handler(body):
            storage_plugin_log.info("DaemonRpc %s %s %s %s" % (body['id'], body['method'], body['args'], body['kwargs']))
            request_id = body['id']
            try:
                result = self._local_call(body['method'], *body['args'], **body['kwargs'])
            except Exception, e:
                result = pickle.dumps(e)
            PluginResponse.send(plugin_name, resource_tag, request_id, result)

        # Enter a loop to service requests until self.stopping is set
        storage_plugin_log.info("Starting DaemonRpc main loop")
        retry_period = 1
        max_retry_period = 60
        while not self._stopping:
            try:
                PluginRequest.handle_all(plugin_name, resource_tag, handler)
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


class StorageDaemon(object):
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
        storage_plugin_log.info("StorageDaemon: Loaded %s plugins, %s sessions" % (len(self.plugins), session_count))

    def remove_resource(self, resource_id):
        # Is there a session to kill?
        kill_session = None
        storage_plugin_log.info("StorageDaemon: removing %s" % resource_id)
        with self._session_lock:
            try:
                kill_session = self._all_sessions[resource_id]
            except KeyError:
                pass

            if kill_session != None:
                kill_session.stop()
                storage_plugin_log.info("StorageDaemon: waiting for session to stop")
                from time import sleep
                while(not kill_session.stopped):
                    sleep(1)

            from chroma_core.lib.storage_plugin.resource_manager import resource_manager
            resource_manager.global_remove_resource(resource_id)

    def start_session(self, resource_id):
        started = False
        timeout = 30
        start_time = datetime.datetime.now()
        while not started:
            with self._session_lock:
                try:
                    session = self._all_sessions[resource_id]
                    started = session.initialized
                except KeyError:
                    started = False

            if datetime.datetime.now() - start_time > datetime.timedelta(seconds = timeout):
                raise Timeout("Timed out after %s seconds waiting for session to start")

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
        storage_plugin_log.info("StorageDaemon: entering main loop")
        for scannable_id, session in self._all_sessions.items():
            session.start()

        while not self.stopping:
            time.sleep(5)

            # Look for any new root resources and start sessions for them
            with self._session_lock:
                for plugin, sessions in self.plugins.items():
                    for rrid in self.root_resource_ids(plugin):
                        if not rrid in sessions:
                            storage_plugin_log.info("StorageDaemon: new session for resource %s" % rrid)
                            s = PluginSession(rrid)
                            sessions[rrid] = s
                            self._all_sessions[rrid] = s
                            s.start()

        storage_plugin_log.info("StorageDaemon: leaving main loop")

        self._stop_sessions()

    def _stop_sessions(self):
        JOIN_TIMEOUT = 5

        storage_plugin_log.info("StorageDaemon: stopping sessions")
        for scannable_id, session in self._all_sessions.items():
            session.stop()
        storage_plugin_log.info("StorageDaemon: joining sessions")
        for scannable_id, session in self._all_sessions.items():
            session.join(timeout = JOIN_TIMEOUT)
            if session.isAlive():
                storage_plugin_log.warning("StorageDaemon: session failed to return in %s seconds, forcing exit" % JOIN_TIMEOUT)
                os._exit(-1)

    def stop(self):
        self.stopping = True
