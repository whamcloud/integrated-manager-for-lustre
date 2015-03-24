

import logging
import socket
import subprocess
import tempfile
import time
import xmlrpclib
import sys
import os

from ConfigParser import ConfigParser
from StringIO import StringIO
from django.utils.unittest import TestCase
import settings

from chroma_core.lib.util import site_dir
from tests.utils import wait

log = logging.getLogger(__name__)


class SupervisorTestCase(TestCase):
    """A test case which starts and stops supervisor services"""

    SERVICES = []
    PORTS = {  # service ports to wait on binding
        'http_agent': [settings.HTTP_AGENT_PORT],
        'nginx': [settings.HTTPS_FRONTEND_PORT, settings.HTTP_FRONTEND_PORT],
        'view_server': [settings.VIEW_SERVER_PORT]
    }
    TIMEOUT = 5  # default timeout to wait for services to start
    CONF = os.path.join(site_dir(), "supervisord.conf")
    TEST_USERNAME = 'test'
    TEST_PASSWORD = 'asiyud97sdyuias'
    TEST_PORT = 9876

    def __init__(self, *args, **kwargs):
        super(SupervisorTestCase, self).__init__(*args, **kwargs)
        self._supervisor = None
        self._tmp_conf = None

    def _wait_for_supervisord(self):
        try:
            self._wait_for_port(self.TEST_PORT)
        except AssertionError:
            rc = self._supervisor.poll()
            if rc is not None:
                stdout, stderr = self._supervisor.communicate()
                log.error("supervisord stdout: %s" % stdout)
                log.error("supervisord stderr: %s" % stderr)
                log.error("supervisord rc = %s" % rc)
                raise AssertionError("supervisord terminated prematurely with status %s" % rc)
            else:
                raise

    def _wait_for_port(self, port):
        log.info("Waiting for port %s..." % port)
        for index in wait(self.TIMEOUT):
            try:
                return socket.socket().connect(('localhost', port))
            except socket.error:
                pass
        raise

    def setUp(self):
        cfg_stringio = StringIO(open(self.CONF).read())
        cp = ConfigParser()
        cp.readfp(cfg_stringio)
        self.programs = []
        for section in cp.sections():
            if section.startswith("program:"):
                progname = section.split("program:")[1]
                self.programs.append(progname)
                cp.set(section, 'autostart', 'false')

        cp.set("inet_http_server", "port", "127.0.0.1:%s" % self.TEST_PORT)
        cp.set("inet_http_server", "username", self.TEST_USERNAME)
        cp.set("inet_http_server", "password", self.TEST_PASSWORD)

        cp.set("supervisorctl", "username", self.TEST_USERNAME)
        cp.set("supervisorctl", "password", self.TEST_PASSWORD)
        cp.set("supervisorctl", "serverurl", "http://localhost:%s/" % self.TEST_PORT)

        self._tmp_conf = tempfile.NamedTemporaryFile(delete = False)
        cp.write(self._tmp_conf)
        self._tmp_conf.close()
        log.debug("Wrote supervisor config to %s" % self._tmp_conf.name)

        cmdline = ["supervisord", "-n", "-c", self._tmp_conf.name]

        self._supervisor = subprocess.Popen(cmdline, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        log.info("Started supervisord")

        try:
            self._wait_for_supervisord()

            self._xmlrpc = xmlrpclib.Server("http://%s:%s@localhost:%s/RPC2" % (self.TEST_USERNAME, self.TEST_PASSWORD, self.TEST_PORT))

            for service in self.SERVICES:
                log.info("Starting service '%s'" % service)
                self.start(service)
            for service in set(self.SERVICES) - set(self.PORTS):
                self.assertRunning(service, uptime=self.TIMEOUT)
        except:
            # Ensure we don't leave a supervisor process behind
            self.tearDown()
            raise

    def tearDown(self):
        test_failed = (sys.exc_info() != (None, None, None))

        if test_failed:
            log.info(self._xmlrpc.system.listMethods())
            log_chunk = self._xmlrpc.supervisor.readLog(0, 4096)
            log.error("Supervisor log: %s" % log_chunk)

        if self._supervisor is not None:
            try:
                self._xmlrpc.supervisor.shutdown()
                stdout, stderr = self._supervisor.communicate()
                # Echo these at the end: by outputting using sys.std* rather than
                # letting the subprocess write directly, this verbose output can be
                # captured by nose and only output on failure.
                sys.stdout.write(stdout)
                sys.stdout.write(stderr)
            except:
                self._supervisor.kill()
            finally:
                self._supervisor = None

        if self._tmp_conf and os.path.exists(self._tmp_conf.name):
            os.unlink(self._tmp_conf.name)

    def start(self, program):
        self._xmlrpc.supervisor.startProcess(program)
        for port in self.PORTS.get(program, []):
            self._wait_for_port(port)
        self.assertRunning(program)

    def stop(self, program):
        self._xmlrpc.supervisor.stopProcess(program)
        self.assertStopped(program)

    def restart(self, program):
        self.stop(program)
        self.start(program)

    def assertRunning(self, program, uptime=0):
        info = self._xmlrpc.supervisor.getProcessInfo(program)
        self.assertEqual(info['statename'], "RUNNING")
        time.sleep(max(0, uptime + info['start'] - info['now']))

    def assertStopped(self, program):
        info = self._xmlrpc.supervisor.getProcessInfo(program)
        self.assertEqual(info['statename'], "STOPPED")

    def assertResponseOk(self, response):
        self.assertTrue(response.ok, "%s: %s" % (response.status_code, response.content))

    def assertExitedCleanly(self, program_name):
        info = self._xmlrpc.supervisor.getProcessInfo(program_name)
        try:
            self.assertEqual(info['exitstatus'], 0, "%s exitstatus=%s (detail: %s)" % (program_name, info['exitstatus'], info))
        except AssertionError:
            log.error("%s stdout: %s" % (program_name, self._xmlrpc.supervisor.readProcessStdoutLog(program_name, 0, 4096)))
            log.error("%s stderr: %s" % (program_name, self._xmlrpc.supervisor.readProcessStderrLog(program_name, 0, 4096)))
            log.error(self.tail_log("%s.log" % program_name))
            log.error(self.tail_log("supervisord.log"))
            raise

    def tail_log(self, log_name):
        with open(log_name) as log_file:
            log_tail = ''.join(log_file.readlines()[-20:])
        return """
Tail for %s:
------------------------------
%s
""" % (log_name, log_tail)
