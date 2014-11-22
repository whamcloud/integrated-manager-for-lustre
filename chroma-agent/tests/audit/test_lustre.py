import tempfile
import unittest
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


class TestObdfilterAuditReadingJobStats(unittest.TestCase):
    """Test that reading job stats will work assuming stats proc file is normal

    Actual reading of the file is simulated through mocks in this test class
    """

    def setUp(self):
        self.audit = ObdfilterAudit()
        self.initial_read_yam_file_func = self.audit._read_job_stats_yaml_file

    def tearDown(self):
        self.audit._read_yaml_file = self.initial_read_yam_file_func

    def test_snapshot_time(self):
        """If a stats file is available, can it be read, and is snapshot time controlling response"""

        #  simulate job stats turned off
        self.audit._read_job_stats_yaml_file = lambda target_name: None
        res = self.audit.read_job_stats('OST0000')

        self.assertEqual(res, [], res)
        self.assertEqual(self.audit.job_stat_last_snapshot_time, {}, self.audit.job_stat_last_snapshot_time)

        #  simulate job stats turned on, but has nothing to report, same return as off
        self.audit._read_job_stats_yaml_file = lambda target_name: []
        res = self.audit.read_job_stats('OST0000')
        self.assertEqual(res, [], res)
        self.assertEqual(self.audit.job_stat_last_snapshot_time, {}, self.audit.job_stat_last_snapshot_time)

        #  This sample stats file output for next 2 tests
        self.audit._read_job_stats_yaml_file = lambda target_name: [{'job_id': 16,
                                                        'snapshot_time': 1416616379,
                                                        'read': {'samples': 0,
                                                                   'unit': 'bytes',
                                                                    'min': 0,
                                                                    'max': 0,
                                                                    'sum': 0},
                                                         'write': {'samples': 1,
                                                                     'unit': 'bytes',
                                                                     'min': 102400,
                                                                     'max': 102400,
                                                                     'sum': 102400}
                                                        }]

        #  Test that the reading adds the record to the snapshot dict, and returns it
        res = self.audit.read_job_stats('OST0000')
        self.assertEqual(self.audit.job_stat_last_snapshot_time, {16: 1416616379}, self.audit.job_stat_last_snapshot_time)
        self.assertEqual(len(res), 1, res)

        # Second read, no change in proc file, so no change in snapshot dict (same value), and returning nothing
        res = self.audit.read_job_stats('OST0000')
        self.assertEqual(res, [], res)
        self.assertEqual(self.audit.job_stat_last_snapshot_time, {16: 1416616379}, self.audit.job_stat_last_snapshot_time)

        #  Simulate new job stats proc file was updated with new snapshot_time for job 16
        self.audit._read_job_stats_yaml_file = lambda target_name: [{'job_id': 16,
                                                         'snapshot_time': 1416616599,
                                                         'read': {'samples': 0,
                                                                   'unit': 'bytes',
                                                                   'min': 0,
                                                                   'max': 0,
                                                                   'sum': 0},
                                                         'write': {'samples': 1,
                                                                    'unit': 'bytes',
                                                                    'min': 102400,
                                                                    'max': 102400,
                                                                    'sum': 102400}
                                                        }]

        #  Test that only one record is in the cache, the latest record, and that this new record is returned
        res = self.audit.read_job_stats('OST0000')
        self.assertTrue({16: 1416616379} not in self.audit.job_stat_last_snapshot_time.items(), self.audit.job_stat_last_snapshot_time)
        self.assertEqual(self.audit.job_stat_last_snapshot_time, {16: 1416616599}, self.audit.job_stat_last_snapshot_time)
        self.assertEqual(len(res), 1, res)
        self.assertEqual(res[0]['snapshot_time'], 1416616599, res)

    def test_snapshot_time_autoclear(self):
        """Test that the cache holds only active jobs after a clear"""

        self.audit._read_job_stats_yaml_file = lambda target_name: [{'job_id': 16,
                                                         'snapshot_time': 1416616379,
                                                         'read': {'samples': 0,
                                                                   'unit': 'bytes',
                                                                   'min': 0,
                                                                   'max': 0,
                                                                   'sum': 0},
                                                         'write': {'samples': 1,
                                                                    'unit': 'bytes',
                                                                    'min': 102400,
                                                                    'max': 102400,
                                                                    'sum': 102400}
                                                        }]

        #  Add this stat to the cache
        res = self.audit.read_job_stats('OST0000')

        #  Next stat shows a new job_id, and DOES NOT SHOW the old id 16.  This means 16 is no longer reporting
        #  This situation can happen in Lustre does an autoclear between these to samples, and 16 has nothing to report.
        self.audit._read_job_stats_yaml_file = lambda target_name: [{'job_id': 17,
                                                         'snapshot_time': 1416616399,
                                                         'read': {'samples': 0,
                                                                   'unit': 'bytes',
                                                                   'min': 0,
                                                                   'max': 0,
                                                                   'sum': 0},
                                                         'write': {'samples': 1,
                                                                    'unit': 'bytes',
                                                                    'min': 102400,
                                                                    'max': 102400,
                                                                    'sum': 102400}
                                                        }]

        #  Test that the cache only have the job_id 17, and not 16 anymore, and that the return is only for 17.
        res = self.audit.read_job_stats('OST0000')
        self.assertEqual(self.audit.job_stat_last_snapshot_time, {17: 1416616399}, self.audit.job_stat_last_snapshot_time)
        self.assertEqual(len(res), 1, res)
        self.assertFalse(16 in (r['job_id'] for r in res), res)
        self.assertTrue(17 in (r['job_id'] for r in res), res)


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
