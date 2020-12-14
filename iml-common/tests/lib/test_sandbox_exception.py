import mock
import unittest
from iml_common.lib.exception_sandbox import exceptionSandBox


class FencingTestCase(unittest.TestCase):

    mock_logger = mock.Mock()

    @exceptionSandBox(mock_logger, 1)
    def function1(self):
        if self.raise_exception:
            raise Exception()

        return 2

    def test_no_exception_debug(self):
        self.raise_exception = False

        self.assertEqual(self.function1(), 2)

    def test_exception_debug(self):
        self.raise_exception = True

        self.assertEqual(self.function1(), 1)
        self.mock_logger.debug.assert_called_once()
