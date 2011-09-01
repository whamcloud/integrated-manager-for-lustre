import unittest
import tempfile
import os, shutil
import hydra_agent.audit.lustre
from hydra_agent.audit.local import LocalAudit
from hydra_agent.audit.lustre import *

class TestLocalLustreMetrics(unittest.TestCase):
    def setUp(self):
        self.tests = os.path.join(os.path.dirname(__file__), '..')

    def test_mdsmgs_metrics(self):
        """Test that the various MGS/MDS metrics are collected and aggregated."""
        audit = LocalAudit()
        audit.fscontext = os.path.join(self.tests,
                                     "data/lustre_versions/2.0.66/mds_mgs")
        metrics = audit.metrics()['raw']['lustre']
        assert metrics['target']['lustre-MDT0000']['filesfree'] == 511954
        assert metrics['target']['MGS']['num_exports'] == 4
        assert metrics['lnet']['send_count'] == 218887

    def test_oss_metrics(self):
        """Test that the various OSS metrics are collected and aggregated."""
        audit = LocalAudit()
        audit.fscontext = os.path.join(self.tests,
                                     "data/lustre_versions/2.0.66/oss")
        metrics = audit.metrics()['raw']['lustre']
        assert metrics['target']['lustre-OST0000']['filesfree'] == 127575
        assert metrics['lnet']['recv_count'] == 547181

class TestMdtMetrics(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = MdtAudit()
        self.audit.fscontext = self.test_root
        self.metrics = self.audit.metrics()['raw']['lustre']['target']

    def test_mdt_int_metrics(self):
        """Test that the mdt simple integer metrics are collected."""
        int_list = "num_exports kbytestotal kbytesfree filestotal filesfree".split()
        for metric in int_list:
            assert metric in self.metrics['lustre-MDT0000'].keys()

    def test_mdt_filesfree(self):
        """Test that mdt int metrics are sane."""
        assert self.metrics['lustre-MDT0000']['filesfree'] == 511954

class TestLnetMetrics(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = LnetAudit()
        self.audit.fscontext = self.test_root
        self.metrics = self.audit.metrics()

    def test_lnet_send_count(self):
        """Test that LNet metrics look sane."""
        assert self.metrics['raw']['lustre']['lnet']['send_count'] == 218887

class TestMgsMetrics(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        self.audit = MgsAudit()
        self.audit.fscontext = self.test_root
        self.metrics = self.audit.metrics()['raw']['lustre']['target']['MGS']

    def test_mgs_stats_list(self):
        """Test that a representative sample of mgs stats is collected."""
        stats_list = "req_waittime req_qdepth req_active req_timeout reqbuf_avail ldlm_plain_enqueue mgs_connect mgs_target_reg obd_ping llog_origin_handle_create llog_origin_handle_next_block llog_origin_handle_read_header".split()
        for stat in stats_list:
            assert stat in self.metrics['stats'].keys()

    def test_mgs_stats_vals(self):
        """Test that the mgs stats contain the correct values."""
        assert self.metrics['stats']['reqbuf_avail']['units'] == "bufs"
        assert self.metrics['stats']['mgs_connect']['sumsquare'] == 74038

    def test_mgs_int_metrics(self):
        """Test that the mgs simple integer metrics are collected."""
        int_list = "num_exports threads_started threads_min threads_max".split()
        for metric in int_list:
            assert metric in self.metrics.keys()

    def test_mgs_threads_max(self):
        """Test that mgs int metrics are sane."""
        assert self.metrics['threads_max'] == 32

class TestObdfilterMetrics(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.0.66/oss")
        self.audit = ObdfilterAudit()
        self.audit.fscontext = self.test_root
        self.metrics = self.audit.metrics()['raw']['lustre']['target']

    def test_obdfilter_stats_list(self):
        """Test that a representative sample of obdfilter stats is collected."""
        stats_list = "read_bytes write_bytes get_page cache_access cache_hit cache_miss get_info set_info_async connect reconnect disconnect statfs create destroy punch sync preprw commitrw llog_init llog_connect ping".split()
        for stat in stats_list:
            assert stat in self.metrics['lustre-OST0000']['stats'].keys()

    def test_obdfilter_stats_vals(self):
        """Test that the obdfilter stats contain the correct values."""
        assert self.metrics['lustre-OST0000']['stats']['cache_hit']['units'] == "pages"
        assert self.metrics['lustre-OST0001']['stats']['write_bytes']['sum'] == 15260975104
        assert self.metrics['lustre-OST0002']['stats']['read_bytes']['count'] == 1842
        assert self.metrics['lustre-OST0003']['stats']['statfs']['count'] == 14503

    def test_obdfilter_int_metrics(self):
        """Test that the obdfilter simple integer metrics are collected."""
        int_list = "num_exports kbytestotal kbytesfree kbytesavail filestotal filesfree tot_dirty tot_granted tot_pending".split()
        for metric in int_list:
            assert metric in self.metrics['lustre-OST0000'].keys()

    def test_obdfilter_filestotal(self):
        """Test that obdfilter int metrics are sane."""
        assert self.metrics['lustre-OST0003']['filestotal'] == 128000
