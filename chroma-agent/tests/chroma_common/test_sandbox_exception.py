import mock

from django.utils import unittest
from chroma_agent.chroma_common.lib.exception_sandbox import ExceptionSandBox, exceptionSandBox


class FencingTestCase(unittest.TestCase):

    def function1(self):
        with ExceptionSandBox(mock.Mock()):
            if self.raise_exception:
                raise Exception()

        return 0

    @exceptionSandBox(mock.Mock(), 1)
    def function2(self):
        if self.raise_exception:
            raise Exception()

        return 2

    def test_no_exception_debug(self):
        ExceptionSandBox.enable_debug(True)
        self.raise_exception = False

        self.assertEqual(self.function1(), 0)
        self.assertEqual(self.function2(), 2)

    def test_no_exception_no_debug(self):
        ExceptionSandBox.enable_debug(False)
        self.raise_exception = False

        self.assertEqual(self.function1(), 0)
        self.assertEqual(self.function2(), 2)

    def test_exception_debug(self):
        ExceptionSandBox.enable_debug(True)
        self.raise_exception = True

        self.assertRaises(Exception, self.function1)
        self.assertRaises(Exception, self.function2)

    def test_exception_no_debug(self):
        ExceptionSandBox.enable_debug(False)
        self.raise_exception = True

        self.assertEqual(self.function1(), 0)
        self.assertEqual(self.function2(), 1)
