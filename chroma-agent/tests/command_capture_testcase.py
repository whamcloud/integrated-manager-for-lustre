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
                    if result[0]:
                        raise chroma_agent.chroma_common.lib.shell.CommandExecutionError(result[0],
                                                                                         args,
                                                                                         result[1],
                                                                                         result[2])
                    return result[1]
            else:
                raise OSError(2, 'No such file or directory', args[0])

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
            else:
                return (2, "", 'No such file or directory')

        self._old_run = chroma_agent.chroma_common.lib.shell.run
        chroma_agent.chroma_common.lib.shell.run = fake_run

    def assertRan(self, command):
        self.assertIn(command, self._command_history)

    def tearDown(self):
        chroma_agent.chroma_common.lib.shell.try_run = self._old_try_run
        chroma_agent.chroma_common.lib.shell.run = self._old_run
