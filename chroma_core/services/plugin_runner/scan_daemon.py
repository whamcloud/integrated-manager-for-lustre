# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import threading
import datetime
import time
import sys
import traceback

from chroma_core.services.log import log_register
from chroma_core.models.storage_plugin import StorageResourceRecord
from chroma_core.models.storage_plugin import StorageResourceOffline


log = log_register(__name__.split(".")[-1])


class ScanDaemon(object):
    """
    This class manages a set of threads, one per `ScannableResource` that periodically invoke
    the callbacks of the plugin associated with the resource.  Typically those callbacks perform
    some network I/O to interrogate the state of the resource.

    For example, if you have a plugin called MyPlugin which has a MyController class that inherits
    from ScannableResource, and the user has created an instance of the MyController class, then
    this class creates a thread for that instance of MyController, and invokes the
    MyPlugin.[initial_scan, update_scan, teardown] functions for that instance.

    Creates a plugin instance for each ScannableResource.

    """

    def __init__(self, resource_manager):
        self.stopping = False

        self._resource_manager = resource_manager
        self._session_lock = threading.Lock()
        self._all_sessions = {}
        # Map of module name to map of root_resource_id to PluginSession
        self.plugins = {}
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        for p in storage_plugin_manager.loaded_plugins.keys():
            # Create sessions for all root resources
            sessions = {}
            for srr_id in self.root_resource_ids(p):
                session = PluginSession(self._resource_manager, srr_id)
                sessions[srr_id] = session
                self._all_sessions[srr_id] = session

            self.plugins[p] = sessions

        session_count = reduce(lambda x, y: x + y, [len(s) for s in self.plugins.values()])
        log.info("Loaded %s plugins, %s sessions" % (len(self.plugins), session_count))

    def modify_resource(self, resource_id, attrs):
        log.info("modifying %s" % resource_id)
        with self._session_lock:
            try:
                kill_session = self._all_sessions[resource_id]
            except KeyError:
                pass
            else:
                kill_session.stop()
                log.info("waiting for session to stop")
                while not kill_session.stopped:
                    time.sleep(1)
                log.info("stopped.")
                for plugin, sessions in self.plugins.items():
                    if resource_id in sessions:
                        del sessions[resource_id]
                del self._all_sessions[resource_id]

            record = StorageResourceRecord.objects.get(pk=resource_id)
            record.update_attributes(attrs)
            record.save()

        log.info("finished removing %s" % resource_id)

    def remove_resource(self, resource_id):
        # Is there a session to kill?
        log.info("removing %s" % resource_id)
        with self._session_lock:
            try:
                kill_session = self._all_sessions[resource_id]
            except KeyError:
                pass
            else:
                kill_session.stop()
                log.info("waiting for session to stop")
                while not kill_session.stopped:
                    time.sleep(1)
                log.info("stopped.")

            self._resource_manager.global_remove_resource(resource_id)
        log.info("finished removing %s" % resource_id)

    def root_resource_ids(self, plugin):
        """Return the PK of all StorageResourceRecords for 'plugin' which have no parents"""
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        ids = storage_plugin_manager.get_scannable_resource_ids(plugin)

        return ids

    def run(self):
        log.info("entering main loop")
        for scannable_id, session in self._all_sessions.items():
            session.start()

        while not self.stopping:
            time.sleep(5)

            # Look for any new root resources and start sessions for them
            with self._session_lock:
                for plugin, sessions in self.plugins.items():
                    for rrid in self.root_resource_ids(plugin):
                        if not rrid in sessions:
                            log.info("new session for resource %s" % rrid)
                            s = PluginSession(self._resource_manager, rrid)
                            sessions[rrid] = s
                            self._all_sessions[rrid] = s
                            s.start()

        log.info("leaving main loop")

        self._stop_sessions()

    def _stop_sessions(self):
        JOIN_TIMEOUT = 5

        log.info("stopping sessions")
        for scannable_id, session in self._all_sessions.items():
            session.stop()
        log.info("joining sessions")
        for scannable_id, session in self._all_sessions.items():
            session.join(timeout=JOIN_TIMEOUT)
            if session.isAlive():
                log.warning("session failed to return in %s seconds, forcing exit" % JOIN_TIMEOUT)
                os._exit(-1)
        log.info("stop sessions done")

    def stop(self):
        self.stopping = True


class PluginSession(threading.Thread):
    def __init__(self, resource_manager, root_resource_id, *args, **kwargs):
        self._resource_manager = resource_manager
        self.stopped = False
        self.stopping = threading.Event()
        self.root_resource_id = root_resource_id
        self.initialized = False

        super(PluginSession, self).__init__(*args, **kwargs)

    def run(self):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        record = StorageResourceRecord.objects.get(id=self.root_resource_id)
        plugin_klass = storage_plugin_manager.get_plugin_class(record.resource_class.storage_plugin.module_name)

        RETRY_DELAY_MIN = 1
        RETRY_DELAY_MAX = 256
        retry_delay = RETRY_DELAY_MIN
        while not self.stopping.is_set():
            last_retry = datetime.datetime.now()
            try:
                # Note: get a fresh root_resource each time as the Plugin
                # instance will modify it.
                self._scan_loop(plugin_klass, record)
            except Exception:
                run_duration = datetime.datetime.now() - last_retry
                if last_retry and run_duration > datetime.timedelta(seconds=RETRY_DELAY_MAX):
                    # If the last run was long running (i.e. probably ran okay until something went
                    # wrong) then retry quickly.
                    retry_delay = RETRY_DELAY_MIN
                else:
                    # If we've already retried recently, then start backing off.
                    retry_delay *= 2

                log.warning(
                    "Exception in scan loop for resource %s, waiting %ss before restart"
                    % (self.root_resource_id, retry_delay)
                )
                exc_info = sys.exc_info()
                backtrace = "\n".join(traceback.format_exception(*(exc_info or sys.exc_info())))
                log.warning("Backtrace: %s" % backtrace)

                # Wait either retry_delay, or until stopping is set, whichever comes sooner
                self.stopping.wait(timeout=retry_delay)
            else:
                log.info("Session %s: out of scan loop cleanly" % self.root_resource_id)

        log.info("Session %s: Dropped out of retry loop" % self.root_resource_id)
        self.stopped = True

    def _scan_loop(self, plugin_klass, record):
        log.debug("Session %s: starting scan loop" % self.root_resource_id)
        instance = plugin_klass(self._resource_manager, self.root_resource_id)
        # TODO: impose timeouts on plugin calls (especially teardown)
        try:
            log.debug("Session %s: >>initial_scan" % self.root_resource_id)
            instance.do_initial_scan()
            self.initialized = True
            log.debug("Session %s: <<initial_scan" % self.root_resource_id)
            first_update = True
            while not self.stopping.is_set():
                log.debug("Session %s: >>periodic_update (%s)" % (self.root_resource_id, instance.update_period))
                instance.do_periodic_update()
                if first_update:
                    # NB don't mark something as online until the first update has completed, to avoid
                    # flapping if something has a working initial_scan and a failing update_scan
                    StorageResourceOffline.notify(record, False)
                    first_update = False

                log.debug("Session %s: <<periodic_update" % self.root_resource_id)

                self.stopping.wait(instance.update_period)
        except Exception:
            raise
        finally:
            StorageResourceOffline.notify(record, True)
            self.initialized = False
            instance.do_teardown()

    def stop(self):
        self.stopping.set()
