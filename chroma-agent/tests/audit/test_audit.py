from django.utils import unittest
import os
import chroma_agent.device_plugins.audit
from chroma_agent.device_plugins.audit.local import LocalAudit
from chroma_agent.device_plugins.audit.node import NodeAudit
from chroma_agent.device_plugins.audit.lustre import LnetAudit, MdtAudit, MgsAudit


class TestAuditScanner(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")

    def test_audit_scanner(self):
        """chroma_agent.device_plugins.audit.local_audit_classes() should return a list of classes."""
        list = [cls for cls in
                chroma_agent.device_plugins.audit.local_audit_classes(self.test_root)]
        self.assertEqual(list, [LnetAudit, MdtAudit, MgsAudit, NodeAudit])


class TestLocalAudit(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = LocalAudit(fscontext=test_root)

    def test_localaudit_audit_classes(self):
        """LocalAudit.audit_classes() should return a list of classes."""
        self.assertEqual(self.audit.audit_classes(), [LnetAudit, MdtAudit, MgsAudit, NodeAudit])
