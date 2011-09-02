import unittest
import tempfile
import os, shutil
import hydra_agent.audit.lustre
from hydra_agent.audit.lustre import *

class TestLustreAuditClassMethods:
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")

    def test_kmod_is_loaded(self):
        """Test that LustreAudit.kmod_is_loaded() works."""
        assert MgsAudit.kmod_is_loaded(self.test_root)

    def test_device_is_present(self):
        """Test that LustreAudit.device_is_present() works."""
        assert MdtAudit.device_is_present(self.test_root)

    def test_is_available(self):
        """Test that LustreAudit.is_available() works."""
        assert LnetAudit.is_available(self.test_root)

class TestLustreAuditScanner(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")

    def test_audit_scanner(self):
        list = [cls.__name__ for cls in
                hydra_agent.audit.lustre.local_audit_classes(self.test_root)]
        assert list == ['LnetAudit', 'MdtAudit', 'MgsAudit']

class TestLustreAudit:
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = LustreAudit(fscontext=self.test_root)

    def test_version(self):
        assert self.audit.version() == "2.0.66"

    def test_version_info(self):
        assert self.audit.version_info() == (2, 0, 66)

class TestLustreAuditGoodHealth:
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))
        f = open(os.path.join(self.test_root, "proc/fs/lustre/health_check"), "w+")
        f.write("healthy\n")
        f.close()
        self.audit = LustreAudit(fscontext=self.test_root)

    def test_health_check_healthy(self):
        assert self.audit.health_check() == "healthy"

    def test_healthy_true(self):
        assert self.audit.is_healthy() == True

    def tearDown(self):
        shutil.rmtree(self.test_root)

class TestLustreAuditBadHealth:
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))
        f = open(os.path.join(self.test_root, "proc/fs/lustre/health_check"), "w+")
        f.write("NOT HEALTHY\n")
        f.close()
        self.audit = LustreAudit(fscontext=self.test_root)

    def test_health_check_not_healthy(self):
        assert self.audit.health_check() == "NOT HEALTHY"

    def test_healthy_false(self):
        assert self.audit.is_healthy() == False

    def tearDown(self):
        shutil.rmtree(self.test_root)

class TestMdtAudit(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = MdtAudit(fscontext=self.test_root)

    def test_audit_is_available(self):
        assert MdtAudit.is_available(self.test_root) == True

class TestLnetAudit(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = LnetAudit(fscontext=self.test_root)

    def test_audit_is_available(self):
        assert LnetAudit.is_available(self.test_root) == True

class TestObdfilterAudit(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/oss")
        self.audit = ObdfilterAudit(fscontext=self.test_root)

    def test_audit_is_available(self):
        assert ObdfilterAudit.is_available(self.test_root) == True
