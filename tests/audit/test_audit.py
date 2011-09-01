import unittest
import tempfile
import os, shutil
from hydra_agent.fscontext import FileSystemContext
import hydra_agent.audit
from hydra_agent.audit.local import LocalAudit
from hydra_agent.audit.node import NodeAudit
from hydra_agent.audit.lustre import *

class TestAuditScanner(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")

    def test_audit_scanner(self):
        list = [cls.__name__ for cls in
                hydra_agent.audit.local_audit_classes(FileSystemContext(self.test_root))]
        assert list == ['LnetAudit', 'MdtAudit', 'MgsAudit', 'NodeAudit']

class TestLocalAudit(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = LocalAudit()
        self.audit.fscontext = self.test_root

    def test_localaudit_audit_classes(self):
        assert self.audit.audit_classes() == [LnetAudit, MdtAudit, MgsAudit, NodeAudit]
