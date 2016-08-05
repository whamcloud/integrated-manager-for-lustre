import tempfile
import os
import shutil
import chroma_agent.device_plugins.audit.lustre
from chroma_agent.device_plugins.audit.lustre import LnetAudit, MdtAudit, MgsAudit, LustreAudit

from tests.test_utils import PatchedContextTestCase


class TestLustreAuditClassMethods(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        super(TestLustreAuditClassMethods, self).setUp()

    def test_kmod_is_loaded(self):
        """Test that LustreAudit.kmod_is_loaded() works."""
        assert MgsAudit.kmod_is_loaded()

    def test_device_is_present(self):
        """Test that LustreAudit.device_is_present() works."""
        assert MdtAudit.device_is_present()

    def test_is_available(self):
        """Test that LustreAudit.is_available() works."""
        assert LnetAudit.is_available()


class TestLustreAuditScanner(PatchedContextTestCase):
    def test_2x_audit_scanner(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        super(TestLustreAuditScanner, self).setUp()
        list = [cls.__name__ for cls in
                chroma_agent.device_plugins.audit.lustre.local_audit_classes()]
        self.assertEqual(list, ['LnetAudit', 'MdtAudit', 'MgsAudit'])

    def test_18x_audit_scanner(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/1.8.7.80/mds_mgs")
        super(TestLustreAuditScanner, self).setUp()
        list = [cls.__name__ for cls in
                chroma_agent.device_plugins.audit.lustre.local_audit_classes()]
        self.assertEqual(list, ['LnetAudit', 'MdsAudit', 'MgsAudit'])


class TestLustreAudit(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        super(TestLustreAudit, self).setUp()
        self.audit = LustreAudit()

    def test_version(self):
        self.assertEqual(self.audit.version, "2.0.66")

    def test_version_info(self):
        self.assertEqual(self.audit.version_info, self.audit.LustreVersion(2, 0, 66))


class TestGitLustreVersion(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.8.55_144_g75fa74c/mds_mgs")
        super(TestGitLustreVersion, self).setUp()
        self.audit = LustreAudit()

    def test_version(self):
        self.assertEqual(self.audit.version, "2.8.55_144_g75fa74c")

    def test_version_info(self):
        self.assertEqual(self.audit.version_info, self.audit.LustreVersion(2, 8, 55))


class TestMisformedLustreVersion(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.bad/mds_mgs")
        super(TestMisformedLustreVersion, self).setUp()
        self.audit = LustreAudit()

    def test_version(self):
        self.assertEqual(self.audit.version, "2.bad")

    def test_version_info(self):
        self.assertEqual(self.audit.version_info, self.audit.LustreVersion(2, 0, 0))


class TestMissingLustreVersion(PatchedContextTestCase):
    """No idea how this might happen, but it shouldn't crash the audit."""
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        super(TestMissingLustreVersion, self).setUp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))
        self.audit = LustreAudit()

    def test_version(self):
        self.assertEqual(self.audit.version, "0.0.0")

    def test_version_info(self):
        self.assertEqual(self.audit.version_info, self.audit.LustreVersion(0, 0, 0))

    def tearDown(self):
        shutil.rmtree(self.test_root)


class TestLustreAuditGoodHealth(PatchedContextTestCase):
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        super(TestLustreAuditGoodHealth, self).setUp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))
        f = open(os.path.join(self.test_root, "proc/fs/lustre/health_check"), "w+")
        f.write("healthy\n")
        f.close()
        self.audit = LustreAudit()

    def test_health_check_healthy(self):
        self.assertEqual(self.audit.health_check(), "healthy")

    def test_healthy_true(self):
        assert self.audit.is_healthy()

    def tearDown(self):
        shutil.rmtree(self.test_root)


class TestLustreAuditBadHealth(PatchedContextTestCase):
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        super(TestLustreAuditBadHealth, self).setUp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))
        f = open(os.path.join(self.test_root, "proc/fs/lustre/health_check"), "w+")
        f.write("NOT HEALTHY\n")
        f.close()
        self.audit = LustreAudit()

    def test_health_check_not_healthy(self):
        self.assertEqual(self.audit.health_check(), "NOT HEALTHY")

    def test_healthy_false(self):
        assert not self.audit.is_healthy()

    def tearDown(self):
        shutil.rmtree(self.test_root)
