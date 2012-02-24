
import os
import time
import logging
import sys
import traceback
import datetime

from hydra_agent.actions.avahi_publish import ZeroconfService
from hydra_agent.actions.avahi_publish import ZeroconfServiceException

daemon_log = logging.getLogger('daemon')
daemon_log.setLevel(logging.INFO)


def retry_main_loop():
    DEFAULT_BACKOFF = 10
    MAX_BACKOFF = 120
    backoff = DEFAULT_BACKOFF

    while True:
        started_at = datetime.datetime.now()
        try:
            daemon_log.info("Entering main loop")
            loop = MainLoop()
            loop.run()
            # NB I would rather ensure cleanup by using 'with', but this
            # is python 2.4-compatible code
            loop._join_plugin_threads()
        except Exception, e:
            exc_info = sys.exc_info()
            backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
            daemon_log.error("Unhandled exception: %s" % backtrace)
            loop._join_plugin_threads()

            duration = datetime.datetime.now() - started_at
            daemon_log.error("(Ran main loop for %s)" % duration)
            if duration > datetime.timedelta(seconds = DEFAULT_BACKOFF):
                # This was a 'reasonably' long run, reset to the default backoff interval
                # to avoid a historical error causing the backoff to stick at max forever.
                backoff = DEFAULT_BACKOFF

            # We now check for some cases on which we should terminate instead
            # of retrying.
            import socket
            if isinstance(e, socket.error):
                # This is a 'system call interrupted' exception which
                # can result from a signal received during a system call --
                # it's not an internal error, so pass the exception up
                errno, message = e
                if errno == 4:
                    raise
            elif isinstance(e, SystemExit):
                # NB this is redundant in Python >= 2.5 (SystemExit no longer
                # inherits from Exception) but is necessary for Python 2.4
                raise
            else:
                daemon_log.error("Waiting %s seconds before retrying" % backoff)
                time.sleep(backoff)
                if backoff < MAX_BACKOFF:
                    backoff *= 2


def run_main_loop(args):
    """Daemonize and handle unexpected exceptions"""
    if not args.foreground:
        from daemon import DaemonContext
        from daemon.pidlockfile import PIDLockFile

        if os.path.exists(MainLoop.PID_FILE + ".lock") or os.path.exists(MainLoop.PID_FILE):
            pid = int(open(MainLoop.PID_FILE).read())
            try:
                os.kill(pid, 0)
            except OSError:
                # Not running, delete stale PID file
                os.remove(MainLoop.PID_FILE)
                os.remove(MainLoop.PID_FILE + ".lock")
                sys.stderr.write("Removing stale PID file\n")
            else:
                # Running, we should refuse to run
                raise RuntimeError("Daemon is already running (PID %s)" % pid)

        context = DaemonContext(pidfile = PIDLockFile(MainLoop.PID_FILE))
        context.open()
        # NB Have to set up logger after entering DaemonContext because it closes all files when
        # it forks
        handler = logging.FileHandler("/var/log/hydra-agent.log")
        handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
        daemon_log.addHandler(handler)
        daemon_log.info("Starting in the background")
    else:
        context = None
        daemon_log.setLevel(logging.DEBUG)
        daemon_log.addHandler(logging.StreamHandler())
        daemon_log.info("Starting in the foreground")

    if args.publish_zconf:
        # Before entering the main loop, advertize ourselves
        # using Avahi (call this only once per process)
        service = ZeroconfService(name="%s" % os.uname()[1], port=22)
        try:
            service.publish()
        except ZeroconfServiceException, e:
            daemon_log.error("Could not publish the host with Zeroconf: Avahi is not running.  Exiting.")
            if context:
                context.close()
            sys.exit(-1)
        except Exception, e:
            exc_info = sys.exc_info()
            backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
            msg = "Error creating Zeroconf publisher: %s\n\n%s" % (e, backtrace)
            daemon_log.error(msg)
            raise RuntimeError(msg)

        # don't need to call service.unpublish() since the service
        # will be unpublished when this daemon exits

    try:
        retry_main_loop()
    except Exception:
        # Swallow terminating exceptions (they were already logged in
        # retry_main_loop) and proceed to teardown
        pass

    if context:
        context.close()
    daemon_log.info("Terminating")


def send_update(server_url, server_token, update_scan, responses):
    """POST to the UpdateScan API method.
       Returns None on errors"""
    from hydra_agent.actions.host_scan import get_fqdn

    from httplib import BadStatusLine
    import simplejson as json
    import urllib2
    url = server_url + "api/update_scan/"
    req = urllib2.Request(url,
                          headers = {"Content-Type": "application/json"},
                          data = json.dumps({
                                  'fqdn': get_fqdn(),
                                  'token': server_token,
                                  'update_scan': update_scan,
                                  'plugins': responses}))

    response_data = None
    try:
        response = urllib2.urlopen(req)
        # NB hydraapi returns {'errors':, 'response':}
        response_data = json.loads(response.read())
    except urllib2.HTTPError, e:
        daemon_log.error("Failed to post results to %s: %s" % (url, e))
    except urllib2.URLError, e:
        daemon_log.error("Failed to open %s: %s" % (url, e))
    except BadStatusLine, e:
        daemon_log.error("Malformed response header from %s: '%s'" % (url, e.line))
    except ValueError, e:
        daemon_log.error("Malformed response body from %s: '%s'" % (url, e))

    return response_data

import threading


class PluginThread(threading.Thread):
    """A thread for processing requests for a particular plugin (one per plugin)"""
    def __init__(self, server_conf, plugin_name, *args, **kwargs):
        import Queue

        self.queue = Queue.Queue()
        self.finished = False
        self.plugin_name = plugin_name

        self._server_conf = server_conf

        # TODO: look up a request handler from plugin_name (currently
        # just hardcoded to do the stuff for the 'linux' plugin)

        super(PluginThread, self).__init__(*args, **kwargs)

    def set_server_conf(self, server_conf):
        self._server_conf = server_conf

    def run(self):
        import Queue

        # Service requests from self.queue
        daemon_log.info("Starting thread for plugin %s" % self.plugin_name)
        while not self.finished:
            try:
                request = self.queue.get(block = True, timeout = 1)
            except Queue.Empty:
                # Timeout and poll rather than blocking forever, in
                # order to handle self.finished in the outer loop
                continue

            # Fulfil any requests for 'linux' storage plugin
            responses = {}
            responses[self.plugin_name] = {}

            # TODO: This is a kluge while 'linux' is the only plugin we understand:
            # should be dispatching requests to plugins and gathering responses.
            from hydra_agent.actions.device_scan import device_scan
            responses[self.plugin_name][request['id']] = device_scan()

            # NB if we fail to send results we will consume the request and drop
            # the result.
            result = send_update(self._server_conf['url'], self._server_conf['token'], None, responses)
            if result == None:
                daemon_log.error("Failed to send back result for request %s:%s" % (self.plugin_name, request['id']))
            else:
                daemon_log.info("Fulfilled request %s:%s" % (self.plugin_name, request['id']))
        daemon_log.info("Finished thread for plugin %s" % self.plugin_thread)

    def join(self, *args, **kwargs):
        self.finished = True
        super(PluginThread, self).join(*args, **kwargs)

    def stop(self):
        self.finished = True


class MainLoop(object):
    PID_FILE = '/var/run/hydra-agent.pid'

    def __init__(self):
        # Map of plugin name to PluginThread
        self._plugin_threads = {}

    def _enqueue_request(self, server_conf, plugin_name, request):
        try:
            plugin_thread = self._plugin_threads[plugin_name]
        except KeyError:
            plugin_thread = PluginThread(server_conf, plugin_name)
            plugin_thread.start()
            self._plugin_threads[plugin_name] = plugin_thread

        daemon_log.info("Enqueuing request %s:%s" % (plugin_name, request['id']))
        plugin_thread.queue.put(request)

    def _join_plugin_threads(self):
        for thread in self._plugin_threads.values():
            thread.stop()

        for thread in self._plugin_threads.values():
            thread.join()

        self._plugin_threads.clear()

    def run(self):
        # Load server config (server URL etc)
        from hydra_agent.store import AgentStore
        server_conf = AgentStore.get_server_conf()
        if server_conf:
            daemon_log.info("Server configuration loaded (url: %s)" % server_conf['url'])

        # How often to report to a configured server
        report_interval = 10

        # How often to re-read JSON to see if we
        # have a server configured
        config_interval = 10
        from hydra_agent.actions.update_scan import update_scan
        while True:
            if AgentStore.server_conf_changed():
                server_conf = AgentStore.get_server_conf()
                if not server_conf:
                    # If the server configuration has been removed then
                    # stop all plugin threads (no longer possible to service
                    # any requests)
                    daemon_log.info("Server configuration cleared")
                    self._join_plugin_threads()
                else:
                    daemon_log.info("Server configuration changed (url: %s)" % server_conf['url'])
                    # If the server configuration has been changed
                    # then update all plugin threads with the new configuration.
                    for thread in self._plugin_threads.values():
                        thread.set_server_conf(server_conf)
                self._reload_config = False
            elif server_conf:
                from datetime import datetime, timedelta
                reported_at = datetime.now()
                response = send_update(server_conf['url'], server_conf['token'], update_scan(), {'linux': {}})

                if response:
                    daemon_log.debug("Update success")
                    for plugin_name, plugin_requests in response['plugins'].items():
                        for request in plugin_requests:
                            self._enqueue_request(server_conf, plugin_name, request)

                while ((datetime.now() - reported_at) < timedelta(seconds = report_interval)):
                    time.sleep(1)
            else:
                time.sleep(config_interval)
