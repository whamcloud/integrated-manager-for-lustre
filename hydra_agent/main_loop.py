
import os
import time
import logging
from daemon import DaemonContext
from daemon.pidlockfile import PIDLockFile

from hydra_agent.actions.avahi_publish import ZeroconfService

daemon_log = logging.getLogger('daemon')
handler = logging.FileHandler("/var/log/hydra-agent.log")
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
daemon_log.addHandler(handler)
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

    def _send_update(self, server_url, data):
        from hydra_agent.actions.fqdn import get_fqdn

        import simplejson as json
        import urllib2
        url = server_url + "api/update_scan/"
        req = urllib2.Request(url,
                              headers = {"Content-Type": "application/json"},
                              data = json.dumps({'fqdn': get_fqdn(),
                                      'update_scan': data})) 
        try:
            urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            daemon_log.error("Failed to post results to %s: %s" % (url, e))
        except urllib2.URLError, e:
            daemon_log.error("Failed to open %s: %s" % (url, e))

    def run(self, foreground):
        if not foreground:
            context = DaemonContext(pidfile = PIDLockFile(MainLoop.PID_FILE))
            context.open()
            daemon_log.info("Starting in the background")
        else:
            context = None
            daemon_log.setLevel(logging.DEBUG)
            daemon_log.addHandler(logging.StreamHandler())
            daemon_log.info("Starting in the foreground")

        # Before entering the loop, set up avahi
        self._publish_avahi()

        # Try loading the server information (where to send audit info)
        from hydra_agent.store import AgentStore
        server_conf = AgentStore.get_server_conf()

        try:
            report_interval = 10
            from hydra_agent.actions.update_scan import update_scan
            while True:
                if server_conf:
                    self._send_update(server_conf['url'], update_scan())

                time.sleep(report_interval)

                # If we were not yet configured for audit, periodically 
                # check for configuration.
                if not server_conf:
                    server_conf = AgentStore.get_server_conf()
        finally:
            if context:
                context.close()
