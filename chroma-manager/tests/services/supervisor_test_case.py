

from ConfigParser import ConfigParser
from StringIO import StringIO
import socket
import subprocess
import tempfile
import time
from unittest import TestCase
import xmlrpclib
import sys
from chroma_core.lib.util import site_dir
import os


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
        cp.set("inet_http_server", "port", self.TEST_PORT)
        cp.set("inet_http_server", "username", self.TEST_USERNAME)
        cp.set("inet_http_server", "password", self.TEST_PASSWORD)

        cp.add_section('supervisorctl')
        cp.set("supervisorctl", "username", self.TEST_USERNAME)
        cp.set("supervisorctl", "password", self.TEST_PASSWORD)
        cp.set("supervisorctl", "serverurl", "http://localhost:%s/" % self.TEST_PORT)

        cp.add_section('supervisord')

        self._tmp_conf = tempfile.NamedTemporaryFile(delete = False)
        cp.write(self._tmp_conf)
        self._tmp_conf.close()

        cmdline = ["supervisord", "-n", "-c", self._tmp_conf.name]

        self._supervisor = subprocess.Popen(cmdline, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        while True:
            s = socket.socket()
            try:
                s.connect(("localhost", self.TEST_PORT))
            except socket.error:
                time.sleep(1)
            else:
                s.close()
                break

        self._xmlrpc = xmlrpclib.Server("http://%s:%s@localhost:%s/RPC2" % (self.TEST_USERNAME, self.TEST_PASSWORD, self.TEST_PORT))

        for service in self.SERVICES:
            self.start(service)

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
            pass

    def start(self, program):
        self._xmlrpc.supervisor.startProcess('httpd')
        self.assertRunning(program)

    def assertRunning(self, program):
        info = self._xmlrpc.supervisor.getProcessInfo(program)
        self.assertEqual(info['statename'], "RUNNING")
