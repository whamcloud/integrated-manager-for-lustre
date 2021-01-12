import logging
import socket

from unittest import TestCase
import settings

from emf_common.lib import util, shell
from emf_common.lib.service_control import ServiceControlEL7

log = logging.getLogger(__name__)


class SystemdTestCase(TestCase):
    """A test case which starts and stops systemd services"""

    SERVICES = []
    PORTS = {  # service ports to wait on binding
        "emf-http-agent": [settings.HTTP_AGENT_PORT],
        "nginx": [settings.HTTPS_FRONTEND_PORT, settings.HTTP_FRONTEND_PORT],
    }
    TIMEOUT = 5  # default timeout to wait for services to start

    def _wait_for_port(self, port):
        log.info("Waiting for port %s..." % port)
        for _ in util.wait(self.TIMEOUT):
            try:
                return socket.socket().connect(("localhost", port))
            except socket.error:
                pass
        raise

    def setUp(self):
        try:

            for service in self.SERVICES:
                log.info("Starting service '%s'" % service)
                ServiceControlEL7(service).start(retry_time=0.1, validate_time=0)
        except:
            # Ensure we don't leave a systemd unit up
            self.tearDown()
            raise

    def tearDown(self):
        # You can't import this gobally because DJANGO_SETTINGS_MODULE is not initialized yet for some
        # reason, but maybe by the time the code meanders its way to here it will work.
        from chroma_core.services.rpc import RpcClientFactory

        # Shutdown any RPC Threads if they were started. Bit of horrible insider knowledge here.
        if RpcClientFactory._lightweight is False:
            RpcClientFactory.shutdown_threads()
            RpcClientFactory._lightweight = True
            RpcClientFactory._available = True
            RpcClientFactory._instances = {}

        for service in self.SERVICES:
            log.info("Stopping service '%s'" % service)
            ServiceControlEL7(service).stop(retry_time=0.1, validate_time=0)

    def start(self, program):
        ServiceControlEL7(program).start(retry_time=0.1, validate_time=0)
        for port in self.PORTS.get(program, []):
            self._wait_for_port(port)

    def stop(self, program):
        ServiceControlEL7(program).stop(retry_time=0.1, validate_time=0)

    def restart(self, program):
        ServiceControlEL7(program).restart(retry_time=0.1, validate_time=0)

    def assertResponseOk(self, response):
        self.assertTrue(response.ok, "%s: %s" % (response.status_code, response.content))

    def assertExitedCleanly(self, program_name):
        info = shell.Shell.try_run(["systemctl", "show", program_name, "-p", "ExecMainStatus"]).strip()
        self.assertEqual(info, "ExecMainStatus=0", "{0} (detail: {1})".format(program_name, info))

    def tail_log(self, log_name):
        with open(log_name) as log_file:
            log_tail = "".join(log_file.readlines()[-20:])
        return """
Tail for %s:
------------------------------
%s
""" % (
            log_name,
            log_tail,
        )
