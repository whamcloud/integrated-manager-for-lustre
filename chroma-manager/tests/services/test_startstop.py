import mock
import os
import time
import xmlrpclib

from tests.services.supervisor_test_case import SupervisorTestCase


class TestStartStop(SupervisorTestCase):
    """
    Generic tests for things that all services should do
    """

    def test_clean_stop(self):
        # httpd doesn't behave reliably with a fast start/stop (it doesn't like
        # being stopped before it's fully started), exclude it from this test -- we
        # are mainly interested in the behaviour of our own code.
        clean_services = set(self.programs) - set(['httpd', 'celery_periodic', 'celery_jobs'])

        for program_name in clean_services:
            self.start(program_name)

        # Try to avoid killing things while they're still starting, it's too much
        # to ask that they have a zero rc in that situation.
        time.sleep(5)
        for program_name in clean_services:
            self.stop(program_name)
            self.assertExitedCleanly(program_name)

    def test_exits_with_error_stopping_service_without_starting(self):
        for program_name in self.programs:
            with self.assertRaises(xmlrpclib.Fault):
                self.stop(program_name)

    def test_exits_with_error_stopping_thread_without_starting(self):
        from chroma_core.services import ServiceThread

        with mock.patch("os._exit", mock.Mock()):
            thread = ServiceThread("somethread")
            thread.stop()
            os._exit.assert_called_with(-1)
