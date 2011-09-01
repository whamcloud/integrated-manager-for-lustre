import unittest
from hydra_agent.fscontext import FileSystemContext

class TestDefaultFileSystemContext:
    def setUp(self):
        self.fscontext = FileSystemContext()

    def test_abs_relative(self):
        assert self.fscontext.abs("tmp") == "/tmp"

    def test_abs(self):
        assert self.fscontext.abs("/tmp") == "/tmp"

    def test_join(self):
        assert self.fscontext.join("foo", "bar") == "/foo/bar"

class TestAlternateFileSystemContext:
    def setUp(self):
        self.fscontext = FileSystemContext("/alt")

    def test_abs_relative(self):
        assert self.fscontext.abs("tmp") == "/alt/tmp"

    def test_abs(self):
        assert self.fscontext.abs("/tmp") == "/alt/tmp"

    def test_join(self):
        assert self.fscontext.join("foo", "bar") == "/alt/foo/bar"
