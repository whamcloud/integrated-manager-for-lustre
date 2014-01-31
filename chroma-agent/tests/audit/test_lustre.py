import tempfile
import os
import shutil
import chroma_agent.device_plugins.audit.lustre
from chroma_agent.device_plugins.audit.lustre import LnetAudit, MdtAudit, MdsAudit, MgsAudit, ObdfilterAudit, LustreAudit, ClientAudit

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
        self.assertEqual(self.audit.version(), "2.0.66")

    def test_version_info(self):
        self.assertEqual(self.audit.version_info(), (2, 0, 66))


class TestMissingLustreVersion(PatchedContextTestCase):
    """No idea how this might happen, but it shouldn't crash the audit."""
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        super(TestMissingLustreVersion, self).setUp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))
        self.audit = LustreAudit()

    def test_version(self):
        self.assertEqual(self.audit.version(), "0.0.0")

    def test_version_info(self):
        self.assertEqual(self.audit.version_info(), (0, 0, 0))

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


class TestMdtAudit(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        super(TestMdtAudit, self).setUp()
        self.audit = MdtAudit()

    def test_audit_is_available(self):
        assert MdtAudit.is_available()


class TestMdsAudit(PatchedContextTestCase):
    """Test MDS audit for 1.8.x filesystems; unused on 2.x filesystems"""
    def test_audit_is_available(self):
        """Test that MDS audits happen for 1.8.x audits."""
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/1.8.7.80/mds_mgs")
        super(TestMdsAudit, self).setUp()
        self.assertTrue(MdsAudit.is_available())

    def test_mdd_obd_skipped(self):
        """Test that the mdd_obd device is skipped for 2.x audits (HYD-437)"""
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        super(TestMdsAudit, self).setUp()
        self.assertFalse(MdsAudit.is_available())


class TestLnetAudit(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        super(TestLnetAudit, self).setUp()
        self.audit = LnetAudit()

    def test_audit_is_available(self):
        assert LnetAudit.is_available()


class TestObdfilterAudit(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/oss")
        super(TestObdfilterAudit, self).setUp()
        self.audit = ObdfilterAudit()

    def test_audit_is_available(self):
        assert ObdfilterAudit.is_available()


class TestClientAudit(PatchedContextTestCase):
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        super(TestClientAudit, self).setUp()
        os.makedirs(os.path.join(self.test_root, "proc"))
        with open(os.path.join(self.test_root, "proc/mounts"), "w+") as f:
            f.write("10.0.0.129@tcp:/testfs /mnt/lustre_clients/testfs lustre rw 0 0\n")
        self.audit = ClientAudit()

    def test_audit_is_available(self):
        assert ClientAudit.is_available()

    def test_gathered_mount_list(self):
        actual_list = self.audit.metrics()['raw']['lustre_client_mounts']
        expected_list = [dict(mountspec = '10.0.0.129@tcp:/testfs',
                              mountpoint = '/mnt/lustre_clients/testfs')]
        self.assertEqual(actual_list, expected_list)
