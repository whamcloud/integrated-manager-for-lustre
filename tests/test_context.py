import unittest
from hydra_agent.context import Context

class TestDefaultContext:
    def setUp(self):
        self.context = Context()

    def test_abs_relative(self):
        assert self.context.abs("tmp") == "/tmp"

    def test_abs(self):
        assert self.context.abs("/tmp") == "/tmp"

    def test_join(self):
        assert self.context.join("foo", "bar") == "/foo/bar"

class TestAlternateContext:
    def setUp(self):
        self.context = Context("/alt")

    def test_abs_relative(self):
        assert self.context.abs("tmp") == "/alt/tmp"

    def test_abs(self):
        assert self.context.abs("/tmp") == "/alt/tmp"

    def test_join(self):
        assert self.context.join("foo", "bar") == "/alt/foo/bar"
