from django.utils import unittest
from hydra_agent.fscontext import FileSystemContext

class TestDefaultFileSystemContext(unittest.TestCase):
    def setUp(self):
        self.fscontext = FileSystemContext()

    def test_abs_relative(self):
        self.assertEqual(self.fscontext.abs("tmp"), "/tmp")

    def test_abs(self):
        self.assertEqual(self.fscontext.abs("/tmp"), "/tmp")

    def test_join(self):
        self.assertEqual(self.fscontext.join("foo", "bar"), "/foo/bar")

class TestAlternateFileSystemContext(unittest.TestCase):
    def setUp(self):
        self.fscontext = FileSystemContext("/alt")

    def test_abs_relative(self):
        self.assertEqual(self.fscontext.abs("tmp"), "/alt/tmp")

    def test_abs(self):
        self.assertEqual(self.fscontext.abs("/tmp"), "/alt/tmp")

    def test_join(self):
        self.assertEqual(self.fscontext.join("foo", "bar"), "/alt/foo/bar")
