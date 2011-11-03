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
        self.assertEqual(metrics['target']['lustre-MDT0000']['filesfree'], 511954)
        self.assertEqual(metrics['target']['MGS']['num_exports'], 4)
        self.assertEqual(metrics['lnet']['send_count'], 218887)

    def test_oss_metrics(self):
        """Test that the various OSS metrics are collected and aggregated."""
        audit = LocalAudit()
        audit.fscontext = os.path.join(self.tests,
                                     "data/lustre_versions/2.0.66/oss")
        metrics = audit.metrics()['raw']['lustre']
        self.assertEqual(metrics['target']['lustre-OST0000']['filesfree'], 127575)
        self.assertEqual(metrics['lnet']['recv_count'], 547181)

class TestPathologicalUseCases(unittest.TestCase):
    # AKA: The world will always build a better idiot! ;)
    def test_loaded_module_no_stats(self):
        """Loaded module with no stats file should be skipped."""
        # An easily-repeatable example of when this happens is when
        # lnet.ko is loaded but LNet is stopped.
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "proc/sys/lnet"))

        f = open(os.path.join(self.test_root, "proc/modules"), "w+")
        f.write("""
lnet 233888 3 ptlrpc,ksocklnd,obdclass, Live 0xffffffffa076e000
        """)
        f.close()

        # Create dummy nodestats files
        f = open(os.path.join(self.test_root, "proc/meminfo"), "w")
        f.write("MemTotal:        3991680 kB\n")
        f.close()
        f = open(os.path.join(self.test_root, "proc/stat"), "w")
        f.write("cpu  24601 2 33757 3471279 10892 6 676 0 0\n")
        f.close()

        audit = LocalAudit(fscontext=self.test_root)
        assert LnetAudit in audit.audit_classes()

        # this shouldn't raise a runtime error
        audit.metrics()

        shutil.rmtree(self.test_root)

    def test_loaded_module_no_device(self):
        """Loaded module with no device entry should be skipped."""
        # We can hit this case fairly readily simply by unmounting
        # targets and leaving modules loaded.  We can simulate it
        # by creating a /proc/modules file with one of our Audit
        # classes' modules in it and an empty /proc/fs/lustre/devices
        # file.
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "proc/fs/lustre"))

        # Create a modules file with...  I dunno, lnet and mgs entries.
        f = open(os.path.join(self.test_root, "proc/modules"), "w+")
        f.write("""
lnet 233888 3 ptlrpc,ksocklnd,obdclass, Live 0xffffffffa076e000
exportfs 4202 1 fsfilt_ldiskfs, Live 0xffffffffa0d22000
mgs 153919 1 - Live 0xffffffffa0cfa000
mgc 50620 2 mgs, Live 0xffffffffa0a90000
        """)
        f.close()

        # Create an empty devices file
        open(os.path.join(self.test_root, "proc/fs/lustre/devices"), "w").close()

        # Ideally, our audit aggregator should never instantiate the
        # audit in the first place.
        audit = LocalAudit(fscontext=self.test_root)
        assert MgsAudit not in audit.audit_classes()

        # On the other hand, some modules don't have a corresponding
        # device entry, and therefore the audit should be instantiated.
        audit = LocalAudit(fscontext=self.test_root)
        assert LnetAudit in audit.audit_classes()

        shutil.rmtree(self.test_root)

    def test_no_lustre_modules_loaded(self):
        """Audit shouldn't fail if there are no Lustre modules loaded."""
        self.test_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_root, "proc"))

        # Create a modules file with no Lustre modules in it.
        f = open(os.path.join(self.test_root, "proc/modules"), "w+")
        f.write("""
lockd 74268 1 nfs, Live 0xffffffffa0105000
fscache 46761 1 nfs, Live 0xffffffffa00ef000 (T)
nfs_acl 2613 1 nfs, Live 0xffffffffa00e9000
auth_rpcgss 44925 1 nfs, Live 0xffffffffa00d6000
sunrpc 242277 18 nfs,lockd,nfs_acl,auth_rpcgss, Live 0xffffffffa0082000
sd_mod 38196 6 - Live 0xffffffffa006b000
crc_t10dif 1507 1 sd_mod, Live 0xffffffffa0065000
e1000 167605 0 - Live 0xffffffffa0030000
ahci 40197 5 - Live 0xffffffffa001e000
dm_mod 75539 2 dm_mirror,dm_log, Live 0xffffffffa0000000
        """)
        f.close()

        # Create dummy nodestats files
        f = open(os.path.join(self.test_root, "proc/meminfo"), "w")
        f.write("MemTotal:        3991680 kB\n")
        f.close()
        f = open(os.path.join(self.test_root, "proc/stat"), "w")
        f.write("cpu  24601 2 33757 3471279 10892 6 676 0 0\n")
        f.close()

        audit = LocalAudit(fscontext=self.test_root)
        # FIXME: this gethostname() should probably be stubbed out
        import socket
        self.assertEqual(audit.metrics(), {'raw': {'node': {'hostname': socket.gethostname(), 'cpustats': {'usage': 59042, 'total': 3541213}, 'meminfo': {'MemTotal': 3991680}}}})

        shutil.rmtree(self.test_root)

    def tearDown(self):
        # Just to make super-duper sure it's gone.
        try:
            shutil.rmtree(self.test_root)
        except OSError:
            pass

class TestMdtMetrics(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        audit = MdtAudit(fscontext=test_root)
        self.metrics = audit.metrics()['raw']['lustre']['target']

    def test_mdt_stats_list(self):
        """Test that a representative sample of mdt stats is collected."""
        stats_list = "req_waittime req_qdepth req_active req_timeout reqbuf_avail mds_getattr mds_connect mds_getstatus mds_statfs mds_sync mds_getxattr open close unlink mkdir rmdir getxattr".split()
        for stat in stats_list:
            assert stat in self.metrics['lustre-MDT0000']['stats'].keys()

    def test_mdt_stats_vals(self):
        """Test that the mdt stats contain the correct values."""
        stats = self.metrics['lustre-MDT0000']['stats']
        self.assertEqual(stats['mds_getattr']['units'], "usec")
        self.assertEqual(stats['mds_sync']['sum'], 4480017)
        self.assertEqual(stats['mkdir']['units'], "reqs")
        self.assertEqual(stats['unlink']['count'], 50254)

    def test_mdt_int_metrics(self):
        """Test that the mdt simple integer metrics are collected."""
        int_list = "num_exports kbytestotal kbytesfree filestotal filesfree".split()
        for metric in int_list:
            assert metric in self.metrics['lustre-MDT0000'].keys()

    def test_mdt_filesfree(self):
        """Test that mdt int metrics are sane."""
        self.assertEqual(self.metrics['lustre-MDT0000']['filesfree'], 511954)

class TestLnetMetrics(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        audit = LnetAudit(fscontext=test_root)
        self.metrics = audit.metrics()

    def test_lnet_send_count(self):
        """Test that LNet metrics look sane."""
        self.assertEqual(self.metrics['raw']['lustre']['lnet']['send_count'], 218887)

class TestMgsMetrics(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        test_root = os.path.join(tests, "data/lustre_versions/2.0.66/mds_mgs")
        audit = MgsAudit(fscontext=test_root)
        self.metrics = audit.metrics()['raw']['lustre']['target']['MGS']

    def test_mgs_stats_list(self):
        """Test that a representative sample of mgs stats is collected."""
        stats_list = "req_waittime req_qdepth req_active req_timeout reqbuf_avail ldlm_plain_enqueue mgs_connect mgs_target_reg obd_ping llog_origin_handle_create llog_origin_handle_next_block llog_origin_handle_read_header".split()
        for stat in stats_list:
            assert stat in self.metrics['stats'].keys()

    def test_mgs_stats_vals(self):
        """Test that the mgs stats contain the correct values."""
        self.assertEqual(self.metrics['stats']['reqbuf_avail']['units'], "bufs")
        self.assertEqual(self.metrics['stats']['mgs_connect']['sumsquare'], 74038)

    def test_mgs_int_metrics(self):
        """Test that the mgs simple integer metrics are collected."""
        int_list = "num_exports threads_started threads_min threads_max".split()
        for metric in int_list:
            assert metric in self.metrics.keys()

    def test_mgs_threads_max(self):
        """Test that mgs int metrics are sane."""
        self.assertEqual(self.metrics['threads_max'], 32)

class TestObdfilterMetrics(unittest.TestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        test_root = os.path.join(tests, "data/lustre_versions/2.0.66/oss")
        audit = ObdfilterAudit(fscontext=test_root)
        self.metrics = audit.metrics()['raw']['lustre']['target']

    def test_obdfilter_stats_list(self):
        """Test that a representative sample of obdfilter stats is collected."""
        stats_list = "read_bytes write_bytes get_page cache_access cache_hit cache_miss get_info set_info_async connect reconnect disconnect statfs create destroy punch sync preprw commitrw llog_init llog_connect ping".split()
        for stat in stats_list:
            assert stat in self.metrics['lustre-OST0000']['stats'].keys()

    def test_obdfilter_stats_vals(self):
        """Test that the obdfilter stats contain the correct values."""
        self.assertEqual(self.metrics['lustre-OST0000']['stats']['cache_hit']['units'], "pages")
        self.assertEqual(self.metrics['lustre-OST0001']['stats']['write_bytes']['sum'], 15260975104)
        self.assertEqual(self.metrics['lustre-OST0002']['stats']['read_bytes']['count'], 1842)
        self.assertEqual(self.metrics['lustre-OST0003']['stats']['statfs']['count'], 14503)

    def test_obdfilter_int_metrics(self):
        """Test that the obdfilter simple integer metrics are collected."""
        int_list = "num_exports kbytestotal kbytesfree kbytesavail filestotal filesfree tot_dirty tot_granted tot_pending".split()
        for metric in int_list:
            assert metric in self.metrics['lustre-OST0000'].keys()

    def test_obdfilter_filestotal(self):
        """Test that obdfilter int metrics are sane."""
        self.assertEqual(self.metrics['lustre-OST0003']['filestotal'], 128000)

    def test_obdfilter_brw_stats(self):
        """Test that obdfilter brw_stats are collected at all."""
        assert 'brw_stats' in self.metrics['lustre-OST0000']

    def test_obdfilter_brw_stats_histograms(self):
        """Test that obdfilter brw_stats are grouped by histograms."""
        hist_list = "pages discont_pages discont_blocks dio_frags rpc_hist io_time disk_iosize".split()
        for name in hist_list:
            assert name in self.metrics['lustre-OST0000']['brw_stats'].keys()

    def test_obdfilter_brw_stats_hist_vals(self):
        """Test that obdfilter brw_stats contain sane values."""
        hist = self.metrics['lustre-OST0000']['brw_stats']['disk_iosize']
        self.assertEqual(hist['units'], "ios")
        self.assertEqual(hist['buckets']['128K']['read']['count'], 784)
        self.assertEqual(hist['buckets']['8K']['read']['pct'], 0)
        self.assertEqual(hist['buckets']['64K']['read']['cum_pct'], 23)

        hist = self.metrics['lustre-OST0000']['brw_stats']['discont_blocks']
        self.assertEqual(hist['units'], "rpcs")
        self.assertEqual(hist['buckets']['1']['write']['count'], 288)
        self.assertEqual(hist['buckets']['17']['write']['pct'], 0)
        self.assertEqual(hist['buckets']['31']['write']['cum_pct'], 100)

    def test_obdfilter_brw_stats_empty_buckets(self):
        """Test that brw_stats hists on a fresh OST (no traffic) have empty buckets."""
        hist = self.metrics['lustre-OST0003']['brw_stats']['pages']
        self.assertEqual(hist['buckets'], {})
