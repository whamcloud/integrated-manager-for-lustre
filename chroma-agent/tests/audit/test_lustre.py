from django.utils import unittest
import tempfile
import os
import shutil
import chroma_agent.audit.lustre
from chroma_agent.audit.lustre import LnetAudit, MdtAudit, MdsAudit, MgsAudit, ObdfilterAudit, LustreAudit


class TestLustreAuditClassMethods(unittest.TestCase):
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
    def test_2x_audit_scanner(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        list = [cls.__name__ for cls in
                chroma_agent.audit.lustre.local_audit_classes(test_root)]
        self.assertEqual(list, ['LnetAudit', 'MdtAudit', 'MgsAudit'])

    def test_18x_audit_scanner(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        test_root = os.path.join(tests, "data/lustre_versions/1.8.7.80/mds_mgs")
        list = [cls.__name__ for cls in
                chroma_agent.audit.lustre.local_audit_classes(test_root)]
        self.assertEqual(list, ['LnetAudit', 'MdsAudit', 'MgsAudit'])


class TestLustreAudit(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = LustreAudit(fscontext=self.test_root)

    def test_version(self):
        self.assertEqual(self.audit.version(), "2.0.66")

    def test_version_info(self):
        self.assertEqual(self.audit.version_info(), (2, 0, 66))


class TestMissingLustreVersion(unittest.TestCase):
    """No idea how this might happen, but it shouldn't crash the audit."""
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))
        self.audit = LustreAudit(fscontext=self.test_root)

    def test_version(self):
        self.assertEqual(self.audit.version(), "0.0.0")

    def test_version_info(self):
        self.assertEqual(self.audit.version_info(), (0, 0, 0))

    def tearDown(self):
        shutil.rmtree(self.test_root)


class TestLustreAuditGoodHealth(unittest.TestCase):
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))
        f = open(os.path.join(self.test_root, "proc/fs/lustre/health_check"), "w+")
        f.write("healthy\n")
        f.close()
        self.audit = LustreAudit(fscontext=self.test_root)

    def test_health_check_healthy(self):
        self.assertEqual(self.audit.health_check(), "healthy")

    def test_healthy_true(self):
        assert self.audit.is_healthy()

    def tearDown(self):
        shutil.rmtree(self.test_root)


class TestLustreAuditBadHealth(unittest.TestCase):
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))
        f = open(os.path.join(self.test_root, "proc/fs/lustre/health_check"), "w+")
        f.write("NOT HEALTHY\n")
        f.close()
        self.audit = LustreAudit(fscontext=self.test_root)

    def test_health_check_not_healthy(self):
        self.assertEqual(self.audit.health_check(), "NOT HEALTHY")

    def test_healthy_false(self):
        assert not self.audit.is_healthy()

    def tearDown(self):
        shutil.rmtree(self.test_root)


class TestMdtAudit(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = MdtAudit(fscontext=self.test_root)

    def test_audit_is_available(self):
        assert MdtAudit.is_available(self.test_root)


class TestMdsAudit(unittest.TestCase):
    """Test MDS audit for 1.8.x filesystems; unused on 2.x filesystems"""
    def test_audit_is_available(self):
        """Test that MDS audits happen for 1.8.x audits."""
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/1.8.7.80/mds_mgs")
        self.assertTrue(MdsAudit.is_available(self.test_root))

    def test_mdd_obd_skipped(self):
        """Test that the mdd_obd device is skipped for 2.x audits (HYD-437)"""
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.assertFalse(MdsAudit.is_available(self.test_root))


class TestLnetAudit(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = LnetAudit(fscontext=self.test_root)

    def test_audit_is_available(self):
        assert LnetAudit.is_available(self.test_root)


class TestObdfilterAudit(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/oss")
        self.audit = ObdfilterAudit(fscontext=self.test_root)

    def test_audit_is_available(self):
        assert ObdfilterAudit.is_available(self.test_root)
