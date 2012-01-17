
import os
import time
import logging

from hydra_agent.actions.avahi_publish import ZeroconfService

daemon_log = logging.getLogger('daemon')
daemon_log.setLevel(logging.INFO)


def run_main_loop(args):
    MainLoop().run(args.foreground)


class MainLoop(object):
    PID_FILE = '/var/run/hydra-agent.pid'

    def _publish_avahi(self):
        service = ZeroconfService(name="%s" % os.uname()[1], port=22)
        service.publish()
        # don't need to call service.unpublish() since the service
        # will be unpublished when this daemon exits

    def _send_update(self, server_url, server_token, update_scan, responses):
        from hydra_agent.actions.fqdn import get_fqdn

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
            response_data = json.loads(response.read())['response']
        except urllib2.HTTPError, e:
            daemon_log.error("Failed to post results to %s: %s" % (url, e))
        except urllib2.URLError, e:
            daemon_log.error("Failed to open %s: %s" % (url, e))
        except BadStatusLine, e:
            daemon_log.error("Malformed response header from %s: '%s'" % (url, e.line))
        except ValueError, e:
            daemon_log.error("Malformed response body from %s: '%s'" % (url, e))

        return response_data

    def _main_loop(self):
        # Before entering the loop, set up avahi
        self._publish_avahi()

        # Try loading the server information (where to send audit info)
        from hydra_agent.store import AgentStore
        server_conf = AgentStore.get_server_conf()

        # How often to report to a configured server
        report_interval = 10

        # How often to re-read JSON to see if we
        # have a server configured
        config_interval = 10
        from hydra_agent.actions.update_scan import update_scan
        from hydra_agent.actions.device_scan import device_scan
        while True:
            if server_conf:
                from datetime import datetime, timedelta
                reported_at = datetime.now()
                response = self._send_update(server_conf['url'], server_conf['token'], update_scan(), {'linux': {}})

                if response:
                    daemon_log.debug("Update success")
                    # This is a kluge while 'linux' is the only plugin we understand:
                    # should be dispatching requests to plugins and gathering responses.
                    responses = {}
                    try:
                        linux_requests = response['plugins']['linux']
                        daemon_log.info("Got requests: %d" % len(response))
                    except KeyError:
                        daemon_log.debug("No requests: %s" % (response))
                        pass
                    else:
                        devices = None
                        if len(linux_requests) > 0:
                            daemon_log.info("Ran device scan")
                            devices = device_scan()
                        else:
                            daemon_log.info("No requests for linux")

                        responses['linux'] = {}
                        for request in linux_requests:
                            daemon_log.info("Fulfilled request %s" % (request['id']))
                            responses['linux'][request['id']] = devices

                    if len(responses) > 0:
                        response = self._send_update(server_conf['url'], server_conf['token'], None, responses)
                while ((datetime.now() - reported_at) < timedelta(seconds = report_interval)):
                    time.sleep(1)

            else:
                time.sleep(config_interval)
                server_conf = AgentStore.get_server_conf()

    def run(self, foreground):
        """Daemonize and handle unexpected exceptions"""
        if not foreground:
            from daemon import DaemonContext
            from daemon.pidlockfile import PIDLockFile

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

        try:
            self._main_loop()
            # NB duplicating context.close between branches because
            # python 2.4 has no 'finally'
            context.close()
        except Exception:
            import sys
            import traceback
            exc_info = sys.exc_info()
            backtrace = '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
            daemon_log.error("Unhandled exception: %s" % backtrace)
            # NB duplicating context.close between branches because
            # python 2.4 has no 'finally'
            context.close()
