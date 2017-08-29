import tempfile
from django.utils.unittest.case import skipIf
import os
import shutil
from chroma_agent.device_plugins.audit.local import LocalAudit
from chroma_agent.device_plugins.audit.lustre import LnetAudit, MdtAudit, MgsAudit, ObdfilterAudit, DISABLE_BRW_STATS

from tests.test_utils import PatchedContextTestCase
from iml_common.test.command_capture_testcase import CommandCaptureTestCase

CMD = ("lctl", "get_param", "lov.lustre-*.target_obd")
lctl_output = "lov.lustre-MDT0000-mdtlov.target_obd=\n0: lustre-OST0000_UUID INACTIVE\n1: lustre-OST0001_UUID INACTIVE\n2: lustre-OST0002_UUID ACTIVE\n3: lustre-OST0003_UUID ACTIVE\n"


class TestLocalLustreMetrics(CommandCaptureTestCase, PatchedContextTestCase):
    def setUp(self):
        self.tests = os.path.join(os.path.dirname(__file__), '..')
        super(TestLocalLustreMetrics, self).setUp()

    def test_mdsmgs_metrics(self):
        """ Test that the various MGS/MDS metrics are collected and aggregated. """
        self.test_root = os.path.join(self.tests,
                                      "data/lustre_versions/2.9.58_86_g2383a62/mds_mgs")

        audit = LocalAudit()

        self.add_command(CMD, stdout=lctl_output)

        metrics = audit.metrics()['raw']['lustre']
        self.assertEqual(metrics['target']['testfs-MDT0000']['filesfree'], 4194037)
        self.assertEqual(metrics['target']['MGS']['num_exports'], 6)
        self.assertEqual(metrics['lnet']['send_count'], 12868)

    def test_mdt_hsm_metrics(self):
        """ Test that the HSM metrics are collected and aggregated. """
        self.test_root = os.path.join(self.tests,
                                      "data/lustre_versions/2.9.58_86_g2383a62/mds_mgs")

        audit = LocalAudit()

        self.add_command(CMD, stdout=lctl_output)

        metrics = audit.metrics()['raw']['lustre']['target']['testfs-MDT0000']['hsm']
        self.assertEqual(metrics['agents']['idle'], 1)
        self.assertEqual(metrics['agents']['busy'], 1)
        self.assertEqual(metrics['agents']['total'], 2)

        self.assertEqual(metrics['actions']['waiting'], 1)
        self.assertEqual(metrics['actions']['running'], 1)
        self.assertEqual(metrics['actions']['succeeded'], 1)
        self.assertEqual(metrics['actions']['errored'], 0)

    def test_oss_metrics(self):
        """Test that the various OSS metrics are collected and aggregated."""
        self.test_root = os.path.join(self.tests,
                                      "data/lustre_versions/2.9.58_86_g2383a62/oss")

        audit = LocalAudit()
        metrics = audit.metrics()['raw']['lustre']
        self.assertEqual(metrics['target']['testfs-OST0000']['filesfree'], 655061)
        self.assertEqual(metrics['lnet']['recv_count'], 50072)
        self.assertEqual(len(metrics['target']), 1)

#    def test_24_oss_metrics(self):
#        """Test that the various OSS metrics are collected and aggregated (2.4+)."""
#        self.test_root = os.path.join(self.tests,
#                                      "data/lustre_versions/2.9.58_86_g2383a62/oss")
#
#        audit = LocalAudit()
#        metrics = audit.metrics()['raw']['lustre']
#        self.assertEqual(metrics['target']['testfs-OST0000']['filesfree'], 655061)
#        self.assertEqual(metrics['lnet']['recv_count'], 50072)
#        self.assertEqual(len(metrics['target']), 1)

    def test_stats(self):
        """ Test that expected values are provided for certain stats used by the UI. """
        self.test_root = os.path.join(self.tests,
                                      "data/lustre_versions/2.9.58_86_g2383a62/oss")

        audit = LocalAudit()
        metrics = audit.metrics()['raw']['lustre']
        self.assertEqual(metrics['target']['testfs-OST0000']['stats']['read_bytes']['units'], "bytes")
        self.assertEqual(metrics['target']['testfs-OST0000']['stats']['read_bytes']['sum'], 0)
        self.assertEqual(metrics['target']['testfs-OST0000']['stats']['write_bytes']['count'], 2)
        self.assertEqual(metrics['target']['testfs-OST0000']['stats']['write_bytes']['sum'], 2468000)


class TestPathologicalUseCases(PatchedContextTestCase):
    # AKA: The world will always build a better idiot! ;)
    def setUp(self):
        self.test_root = tempfile.mkdtemp()
        super(TestPathologicalUseCases, self).setUp()
        os.makedirs(os.path.join(self.test_root, "proc"))
        with open(os.path.join(self.test_root, "proc/mounts"), "w") as f:
            f.write("\n")

    def tearDown(self):
        # Just to make super-duper sure it's gone.
        try:
            shutil.rmtree(self.test_root)
        except OSError:
            pass

    def test_loaded_module_no_stats(self):
        """Loaded modules with no stats files should be skipped."""
        # An easily-repeatable example of when this happens is when
        # lnet.ko is loaded but LNet is stopped.
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

        audit = LocalAudit()
        assert LnetAudit in audit.audit_classes()

        # this shouldn't raise a runtime error
        audit.metrics()

    def test_missing_brw_stats(self):
        """Catch a race where brw_stats hasn't been created yet."""
        os.makedirs(os.path.join(self.test_root, "sys/kernel/debug/lustre"))

        f = open(os.path.join(self.test_root, "proc/modules"), "w+")
        f.write("obdfilter 265823 4 - Live 0xffffffffa06b5000")
        f.close()

        f = open(os.path.join(self.test_root, "sys/kernel/debug/lustre/devices"), "w+")
        f.write("  2 UP obdfilter test-OST0000 test-OST0000_UUID 5")
        f.close()

        # Create dummy nodestats files
        f = open(os.path.join(self.test_root, "proc/meminfo"), "w")
        f.write("MemTotal:        3991680 kB\n")
        f.close()
        f = open(os.path.join(self.test_root, "proc/stat"), "w")
        f.write("cpu  24601 2 33757 3471279 10892 6 676 0 0\n")
        f.close()

        audit = LocalAudit()
        assert ObdfilterAudit in audit.audit_classes()

        # this shouldn't raise a runtime error
        audit.metrics()

    def test_loaded_module_no_device(self):
        """Loaded module with no device entry should be skipped."""
        # We can hit this case fairly readily simply by unmounting
        # targets and leaving modules loaded.  We can simulate it
        # by creating a /proc/modules file with one of our Audit
        # classes' modules in it and an empty devices
        # file.
        os.makedirs(os.path.join(self.test_root, "sys/kernel/debug/lustre"))

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
        open(os.path.join(self.test_root, "sys/kernel/debug/lustre/devices"), "w+").close()

        # Ideally, our audit aggregator should never instantiate the
        # audit in the first place.
        audit = LocalAudit()
        assert MgsAudit not in audit.audit_classes()

        # On the other hand, some modules don't have a corresponding
        # device entry, and therefore the audit should be instantiated.
        audit = LocalAudit()
        assert LnetAudit in audit.audit_classes()

    def test_no_lustre_modules_loaded(self):
        """Audit shouldn't fail if there are no Lustre modules loaded."""

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

        audit = LocalAudit()
        # FIXME: this gethostname() should probably be stubbed out
        import socket
        self.assertEqual(audit.metrics(), {'raw': {'node': {'hostname': socket.gethostname(), 'cpustats': {'iowait': 10892, 'idle': 3471279, 'total': 3540537, 'user': 24601, 'system': 33763}, 'meminfo': {'MemTotal': 3991680}}}})


class TestMdtMetrics(CommandCaptureTestCase, PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.9.58_86_g2383a62/mds_mgs")
        super(TestMdtMetrics, self).setUp()
        self.audit = MdtAudit()
        self.add_command(CMD, stdout=lctl_output)
        self.metrics = self.audit.metrics()['raw']['lustre']['target']

    def test_get_client_count(self):
        self.assertEqual(self.metrics['testfs-MDT0000']['client_count'], 1)

    def test_mdt_stats_list(self):
        """Test that a representative sample of mdt stats is collected."""
        stats_list = "req_waittime " \
                     "req_qdepth " \
                     "req_active " \
                     "req_timeout " \
                     "reqbuf_avail " \
                     "ldlm_ibits_enqueue " \
                     "mds_reint_setattr " \
                     "mds_reint_open " \
                     "mds_getattr " \
                     "mds_connect " \
                     "mds_get_root " \
                     "mds_statfs " \
                     "mds_getxattr " \
                     "obd_ping " \
                     "open " \
                     "close " \
                     "mknod " \
                     "getattr " \
                     "setattr " \
                     "statfs " \
                     "getxattr".split()
        for stat in stats_list:
            assert stat in self.metrics['testfs-MDT0000']['stats'].keys(), "%s is missing" % stat

    def test_mdt_stats_vals(self):
        """Test that the mdt stats contain the correct values."""
        stats = self.metrics['testfs-MDT0000']['stats']
        self.assertEqual(stats['mds_getattr']['units'], "usec")
        self.assertEqual(stats['mds_get_root']['sum'], 15)
        self.assertEqual(stats['mknod']['units'], "reqs")
        self.assertEqual(stats['close']['count'], 8)

    def test_mdt_int_metrics(self):
        """Test that the mdt simple integer metrics are collected."""
        int_list = "client_count kbytestotal kbytesfree filestotal filesfree".split()
        for metric in int_list:
            assert metric in self.metrics['testfs-MDT0000'].keys(), "%s is missing" % metric

    def test_mdt_filesfree(self):
        """Test that mdt int metrics are sane."""
        self.assertEqual(self.metrics['testfs-MDT0000']['filesfree'], 4194037)


class TestLnetMetrics(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.9.58_86_g2383a62/mds_mgs")
        super(TestLnetMetrics, self).setUp()
        audit = LnetAudit()
        self.metrics = audit.metrics()

    def test_lnet_send_count(self):
        """Test that LNet metrics look sane."""
        self.assertEqual(self.metrics['raw']['lustre']['lnet']['send_count'], 12868)


class TestMgsMetrics(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.9.58_86_g2383a62/mds_mgs")
        super(TestMgsMetrics, self).setUp()
        audit = MgsAudit()
        self.metrics = audit.metrics()['raw']['lustre']['target']['MGS']

    def test_mgs_stats_list(self):
        """Test that a representative sample of mgs stats is collected."""
        stats_list = "req_waittime " \
                     "req_qdepth " \
                     "req_active " \
                     "req_timeout " \
                     "reqbuf_avail " \
                     "ldlm_plain_enqueue " \
                     "mgs_connect " \
                     "mgs_target_reg " \
                     "mgs_config_read " \
                     "obd_ping " \
                     "llog_origin_handle_open " \
                     "llog_origin_handle_next_block " \
                     "llog_origin_handle_read_header".split()
        for stat in stats_list:
            assert stat in self.metrics['stats'].keys()

    def test_mgs_stats_vals(self):
        """Test that the mgs stats contain the correct values."""
        self.assertEqual(self.metrics['stats']['reqbuf_avail']['units'], "bufs")
        self.assertEqual(self.metrics['stats']['mgs_connect']['sumsquare'], 380555157)

    def test_mgs_int_metrics(self):
        """Test that the mgs simple integer metrics are collected."""
        int_list = "num_exports threads_started threads_min threads_max".split()
        for metric in int_list:
            assert metric in self.metrics.keys()

    def test_mgs_threads_max(self):
        """Test that mgs int metrics are sane."""
        self.assertEqual(self.metrics['threads_max'], 32)


class TestObdfilterMetrics(PatchedContextTestCase):
    def setUp(self):
        tests = os.path.join(os.path.dirname(__file__), '..')
        self.test_root = os.path.join(tests, "data/lustre_versions/2.9.58_jobstats/oss")
        super(TestObdfilterMetrics, self).setUp()
        audit = ObdfilterAudit()
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
        self.assertEqual(self.metrics['lustre-OST0000']['stats']['read_bytes']['count'], 1892)
        self.assertEqual(self.metrics['lustre-OST0001']['stats']['statfs']['count'], 14472)

    def test_obdfilter_int_metrics(self):
        """Test that the obdfilter simple integer metrics are collected."""
        int_list = "num_exports kbytestotal kbytesfree kbytesavail filestotal filesfree tot_dirty tot_granted tot_pending".split()
        for metric in int_list:
            assert metric in self.metrics['lustre-OST0000'].keys()

    def test_obdfilter_filestotal(self):
        """Test that obdfilter int metrics are sane."""
        self.assertEqual(self.metrics['lustre-OST0001']['filestotal'], 128000)

    @skipIf(DISABLE_BRW_STATS, "BRW stats disabled because of HYD-2307")
    def test_obdfilter_brw_stats(self):
        """Test that obdfilter brw_stats are collected at all."""
        assert 'brw_stats' in self.metrics['lustre-OST0000']

    @skipIf(DISABLE_BRW_STATS, "BRW stats disabled because of HYD-2307")
    def test_obdfilter_brw_stats_histograms(self):
        """Test that obdfilter brw_stats are grouped by histograms."""
        hist_list = "pages discont_pages discont_blocks dio_frags rpc_hist io_time disk_iosize".split()
        for name in hist_list:
            assert name in self.metrics['lustre-OST0000']['brw_stats'].keys()

    @skipIf(DISABLE_BRW_STATS, "BRW stats disabled because of HYD-2307")
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

    @skipIf(DISABLE_BRW_STATS, "BRW stats disabled because of HYD-2307")
    def test_obdfilter_brw_stats_empty_buckets(self):
        """Test that brw_stats hists on a fresh OST (no traffic) have empty buckets."""
        hist = self.metrics['lustre-OST0003']['brw_stats']['pages']
        self.assertEqual(hist['buckets'], {})


class TestJobStats(PatchedContextTestCase):
    def setUp(self):
        self.test_root = os.path.normpath(os.path.join(__file__, '../../data/lustre_versions/2.9.58_jobstats/oss'))
        super(TestJobStats, self).setUp()
        audit = ObdfilterAudit()
        self.metrics = audit.metrics()['raw']['lustre']

    def test(self):
        assert self.metrics['jobid_var'] == 'procname_uid'
        metrics = self.metrics['target']
        for target in ('lustre-OST0001', 'lustre-OST0002', 'lustre-OST0003'):
            assert metrics[target]['job_stats'] == []
        stats = metrics['lustre-OST0000']['job_stats']
        assert [stat['job_id'] for stat in stats] == ['dd.0', 'cp.0']
        assert [stat['snapshot_time'] for stat in stats] == [1381939640, 1381939592]
        assert stats[0]['read']['sum'] == stats[0]['write']['sum'] == 671088640
        assert stats[1]['read']['sum'] == 0 and stats[1]['write']['sum'] == 220986046
