from django.utils import unittest
import chroma_agent.chroma_common.lib.shell


class CommandCaptureTestCase(unittest.TestCase):
    results = {}

    def setUp(self):
        self._command_history = []

        def fake_try_run(args):
            self._command_history.append(args)
            if tuple(args) in self.results:
                result = self.results[tuple(args)]
                if type(result) == str:
                    return result
                else:
                    return result[1]

        self._old_try_run = chroma_agent.chroma_common.lib.shell.try_run
        chroma_agent.chroma_common.lib.shell.try_run = fake_try_run

        def fake_run(args):
            self._command_history.append(args)
            if tuple(args) in self.results:
                result = self.results[tuple(args)]

                if type(result) == str:
                    return (0, self.results[tuple(args)], 0)
                else:
                    return result

        self._old_run = chroma_agent.chroma_common.lib.shell.run
        chroma_agent.chroma_common.lib.shell.run = fake_run

    def assertRan(self, command):
        self.assertIn(command, self._command_history)

    def tearDown(self):
        chroma_agent.chroma_common.lib.shell.try_run = self._old_try_run
        chroma_agent.chroma_common.lib.shell.run = self._old_run
