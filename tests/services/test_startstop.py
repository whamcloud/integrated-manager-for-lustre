import mock
import os
import time

from tests.services.systemd_test_case import SystemdTestCase


class TestStartStop(SystemdTestCase):
    """
    Generic tests for things that all services should do
    """

    def test_clean_stop(self):
        services = [
            "iml-http-agent.service",
            "iml-job-scheduler.service",
            "iml-plugin-runner.service",
            "iml-power-control.service",
            "iml-corosync.service",
            "iml-gunicorn.service",
        ]

        for service in services:
            self.start(service)

        # Try to avoid killing things while they're still starting, it's too much
        # to ask that they have a zero rc in that situation.
        time.sleep(5)
        for service in services:
            self.stop(service)
            self.assertExitedCleanly(service)

    def test_exits_with_error_stopping_thread_without_starting(self):
        from chroma_core.services import ServiceThread

        with mock.patch("os._exit", mock.Mock()):
            thread = ServiceThread("somethread")
            thread.stop()
            os._exit.assert_called_with(-1)
