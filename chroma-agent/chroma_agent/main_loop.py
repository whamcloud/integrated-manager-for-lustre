
import os
import time
import logging
import sys
import traceback
import datetime

from chroma_agent.avahi_publish import ZeroconfService
from chroma_agent.avahi_publish import ZeroconfServiceException

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
        except Exception, e:
            exc_info = sys.exc_info()
            backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
            daemon_log.error("Unhandled exception: %s" % backtrace)

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
        handler = logging.FileHandler("/var/log/chroma-agent.log")
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


def send_update(server_url, server_token, session, started_at, updates):
    """POST to the UpdateScan API method.
       Returns None on errors"""
    from chroma_agent.action_plugins.host_scan import get_fqdn

    from httplib import BadStatusLine
    import simplejson as json
    import urllib2
    url = server_url + "api/agent/"
    req = urllib2.Request(url,
                          headers = {"Content-Type": "application/json"},
                          data = json.dumps({
                                  'session': session,
                                  'fqdn': get_fqdn(),
                                  'token': server_token,
                                  'started_at': started_at.isoformat() + "Z",
                                  'updates': updates}))

    response_data = None
    try:
        response = urllib2.urlopen(req)
        response_data = json.loads(response.read())
    except urllib2.HTTPError, e:
        daemon_log.error("Failed to post results to %s: %s" % (url, e))
        try:
            content = json.loads(e.read())
            daemon_log.error("Exception: %s" % content['traceback'])
        except ValueError:
            daemon_log.error("Unreadable payload")
    except urllib2.URLError, e:
        daemon_log.error("Failed to open %s: %s" % (url, e))
    except BadStatusLine, e:
        daemon_log.error("Malformed response header from %s: '%s'" % (url, e.line))
    except ValueError, e:
        daemon_log.error("Malformed response body from %s: '%s'" % (url, e))

    return response_data


class MainLoop(object):
    PID_FILE = '/var/run/chroma-agent.pid'

    def run(self):
        # Load server config (server URL etc)
        from chroma_agent.store import AgentStore
        server_conf = AgentStore.get_server_conf()
        if server_conf:
            daemon_log.info("Server configuration loaded (url: %s)" % server_conf['url'])

        # How often to report to a configured server
        report_interval = 10

        # How often to re-read JSON to see if we
        # have a server configured
        config_interval = 10
        session_id = None
        session_started = False
        session_counter = None
        session_state = None
        while True:
            if AgentStore.server_conf_changed():
                server_conf = AgentStore.get_server_conf()
                if not server_conf:
                    daemon_log.info("Server configuration cleared")
                else:
                    daemon_log.info("Server configuration changed (url: %s)" % server_conf['url'])
                self._reload_config = False
            elif server_conf:
                from datetime import datetime, timedelta
                # Record the *start* of the reporting cycle (all enclosed
                # data is younger than this time)
                update_started_at = datetime.utcnow()

                updates = {}
                from chroma_agent.plugins import DevicePluginManager
                if session_id and not session_started:
                    daemon_log.info("New session, sending full information")
                    for plugin_name, plugin in DevicePluginManager.get_plugins().items():
                        instance = plugin()
                        session_state[plugin_name] = instance
                        updates[plugin_name] = instance.start_session()
                elif session_id:
                    daemon_log.debug("Continue session, sending update information")
                    for plugin_name, plugin in DevicePluginManager.get_plugins().items():
                        instance = session_state[plugin_name]
                        try:
                            updates[plugin_name] = instance.update_session()
                        except NotImplementedError:
                            pass
                else:
                    daemon_log.debug("No session")
                    pass

                session = {
                        'id': session_id,
                        'counter': session_counter
                        }
                response_data = send_update(server_conf['url'], server_conf['token'], session, update_started_at, updates)
                quick_retry = False
                if response_data:
                    if session_id and response_data['session_id'] != session_id:
                        daemon_log.info("Session %s evicted" % (session_id))
                        session_id = response_data['session_id']
                        session_counter = 0
                        session_started = False
                        session_state = {}
                        quick_retry = True
                    elif not session_id:
                        session_id = response_data['session_id']
                        session_counter = 0
                        session_started = False
                        session_state = {}
                        daemon_log.info("Session %s began" % (session_id))
                        quick_retry = True
                    elif session_id and response_data['session_id'] == session_id:
                        session_started = True
                        session_counter += 1

                if not quick_retry:
                    while ((datetime.utcnow() - update_started_at) < timedelta(seconds = report_interval)):
                        time.sleep(1)
            else:
                time.sleep(config_interval)
