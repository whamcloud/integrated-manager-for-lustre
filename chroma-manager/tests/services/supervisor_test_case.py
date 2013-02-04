

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

from chroma_core.lib.util import site_dir

log = logging.getLogger(__name__)


class SupervisorTestCase(TestCase):
    """A test case which starts and stops supervisor services"""

    SERVICES = []
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

    def _wait_for_port(self, port, timeout = 10):
        log.info("Waiting for port %s..." % port)
        i = 0
        while True:
            s = socket.socket()
            try:
                s.connect(("localhost", port))
            except socket.error:
                if i > timeout:
                    raise AssertionError("Timed out after %s seconds waiting for port %s" % (timeout, port))
                i += 1
                time.sleep(1)
            else:
                s.close()
                log.info("Port %s ready after %s seconds" % (port, i))
                break

    def setUp(self):
        cfg_stringio = StringIO(open(self.CONF).read())
        cp = ConfigParser()
        cp.readfp(cfg_stringio)
        programs = []
        for section in cp.sections():
            if section.startswith("program:"):
                progname = section.split("program:")[1]
                programs.append(progname)
                cp.set(section, 'autostart', 'false')

        cp.add_section('inet_http_server')
        cp.set("inet_http_server", "port", "127.0.0.1:%s" % self.TEST_PORT)
        cp.set("inet_http_server", "username", self.TEST_USERNAME)
        cp.set("inet_http_server", "password", self.TEST_PASSWORD)

        cp.add_section('supervisorctl')
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

            for port in self.PORTS:
                self._wait_for_port(port)
        except:
            # Ensure we don't leave a supervisor process behind
            self.tearDown()
            raise

    def tearDown(self):
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
        self.assertRunning(program)

    def stop(self, program):
        self._xmlrpc.supervisor.stopProcess(program)
        self.assertStopped(program)

    def restart(self, program):
        self.stop(program)
        self.start(program)

    def assertRunning(self, program):
        info = self._xmlrpc.supervisor.getProcessInfo(program)
        self.assertEqual(info['statename'], "RUNNING")

    def assertStopped(self, program):
        info = self._xmlrpc.supervisor.getProcessInfo(program)
        self.assertEqual(info['statename'], "STOPPED")

    def assertResponseOk(self, response):
        self.assertTrue(response.ok, "%s: %s" % (response.status_code, response.content))
