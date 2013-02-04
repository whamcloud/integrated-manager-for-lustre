from tests.services.supervisor_test_case import SupervisorTestCase


class TestStartStop(SupervisorTestCase):
    """
    Generic tests for things that all services should do
    """

    SERVICES = []
    PORTS = []

    def test_clean_stop(self):
        for program_name in self.programs:
            self.start(program_name)
            self.stop(program_name)
            self.assertExitedCleanly(program_name)
