import mock
from django.utils import unittest
from iml_common.test.command_capture_testcase import CommandCaptureTestCase


class PatchedContextTestCase(unittest.TestCase):
    def __init__(self, methodName):
        super(PatchedContextTestCase, self).__init__(methodName)
        self._test_root = None

    def _find_subclasses(self, klass):
        """Introspectively find all descendents of a class"""
        subclasses = []
        for subclass in klass.__subclasses__():
            subclasses.append(subclass)
            subclasses.extend(self._find_subclasses(subclass))
        return subclasses

    @property
    def test_root(self):
        return self._test_root

    @test_root.setter
    def test_root(self, value):
        assert self._test_root == None, "test_root can only be set once per test"

        self._test_root = value

        from chroma_agent.device_plugins.audit import BaseAudit
        for subclass in self._find_subclasses(BaseAudit):
            mock.patch.object(subclass, 'fscontext', self._test_root).start()

        # These classes aren't reliably detected for patching.
        from chroma_agent.device_plugins.audit.node import NodeAudit
        mock.patch.object(NodeAudit, 'fscontext', self._test_root).start()

        self.addCleanup(mock.patch.stopall)