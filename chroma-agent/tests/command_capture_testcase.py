from django.utils import unittest
import chroma_agent.shell


class CommandCaptureTestCase(unittest.TestCase):
    results = {}

    def setUp(self):
        self._command_history = []

        def fake_try_run(args):
            self._command_history.append(args)
            if tuple(args) in self.results:
                return self.results[tuple(args)]

        self._old_try_run = chroma_agent.shell.try_run
        chroma_agent.shell.try_run = fake_try_run

        def fake_run(args):
            self._command_history.append(args)
            if tuple(args) in self.results:
                return self.results[tuple(args)]

        self._old_run = chroma_agent.shell.run
        chroma_agent.shell.run = fake_run

    def assertRan(self, command):
        self.assertIn(command, self._command_history)

    def tearDown(self):
        chroma_agent.shell.try_run = self._old_try_run
        chroma_agent.shell.run = self._old_run
