import unittest
import os
from chroma_agent.device_plugins.audit.lustre import LnetAudit, MdtAudit, MdsAudit, MgsAudit, ObdfilterAudit, LustreAudit

from tests.test_utils import PatchedContextTestCase


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
