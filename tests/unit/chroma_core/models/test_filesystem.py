from chroma_core.lib.cache import ObjectCache
from chroma_core.models import ManagedMgs, ManagedFilesystem, ManagedMdt, ManagedOst, Nid
from tests.unit.chroma_core.helpers import synthetic_host, synthetic_volume_full
from tests.unit.chroma_core.helpers import load_default_profile
from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase


class TestNidStrings(IMLUnitTestCase):
    def setUp(self):
        super(TestNidStrings, self).setUp()

        # If the test that just ran imported storage_plugin_manager, it will
        # have instantiated its singleton, and created some DB records.
        # Django TestCase rolls back the database, so make sure that we
        # also roll back (reset) this singleton.
        import chroma_core.lib.storage_plugin.manager

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = (
            chroma_core.lib.storage_plugin.manager.StoragePluginManager()
        )

        load_default_profile()

    def _host_with_nids(self, address):
        host_nids = {
            "primary-mgs": [Nid.Nid("1.2.3.4", "tcp", 0)],
            "failover-mgs": [Nid.Nid("1.2.3.5", "tcp", 5)],
            "primary-mgs-twonid": [Nid.Nid("1.2.3.4", "tcp", 0), Nid.Nid("4.3.2.1", "tcp", 1)],
            "failover-mgs-twonid": [Nid.Nid("1.2.3.5", "tcp", 5), Nid.Nid("4.3.2.2", "tcp", 1)],
            "othernode": [Nid.Nid("1.2.3.6", "tcp", 0), Nid.Nid("4.3.2.3", "tcp", 1)],
        }
        return synthetic_host(address, host_nids[address])

    def _create_file_system(self, mgt, other):
        fs = ManagedFilesystem.objects.create(mgs=mgt, name="testfs")
        ObjectCache.add(ManagedFilesystem, fs)
        ManagedMdt.create_for_volume(synthetic_volume_full(other).id, filesystem=fs)
        ManagedOst.create_for_volume(synthetic_volume_full(other).id, filesystem=fs)

        return fs

    def test_one_nid_no_failover(self):
        mgs0 = self._host_with_nids("primary-mgs")
        other = self._host_with_nids("othernode")
        mgt, _ = ManagedMgs.create_for_volume(synthetic_volume_full(mgs0).id, name="MGS")
        fs = self._create_file_system(mgt, other)

        self.assertEqual(mgt.nids(), ((u"1.2.3.4@tcp0",),))
        self.assertEqual(fs.mgs_spec(), u"1.2.3.4@tcp0")

    def test_one_nid_with_failover(self):
        mgs0 = self._host_with_nids("primary-mgs")
        mgs1 = self._host_with_nids("failover-mgs")
        other = self._host_with_nids("othernode")
        mgt, _ = ManagedMgs.create_for_volume(synthetic_volume_full(mgs0, secondary_hosts=[mgs1]).id, name="MGS")
        fs = self._create_file_system(mgt, other)

        self.assertEqual(mgt.nids(), ((u"1.2.3.4@tcp0",), (u"1.2.3.5@tcp5",)))
        self.assertEqual(fs.mgs_spec(), u"1.2.3.4@tcp0:1.2.3.5@tcp5")

    def test_two_nids_no_failover(self):
        mgs0 = self._host_with_nids("primary-mgs-twonid")
        other = self._host_with_nids("othernode")
        mgt, _ = ManagedMgs.create_for_volume(synthetic_volume_full(mgs0).id, name="MGS")
        fs = self._create_file_system(mgt, other)

        self.assertEqual(mgt.nids(), ((u"1.2.3.4@tcp0", u"4.3.2.1@tcp1"),))
        self.assertEqual(fs.mgs_spec(), u"1.2.3.4@tcp0,4.3.2.1@tcp1")

    def test_two_nids_with_failover(self):
        mgs0 = self._host_with_nids("primary-mgs-twonid")
        mgs1 = self._host_with_nids("failover-mgs-twonid")
        other = self._host_with_nids("othernode")
        mgt, _ = ManagedMgs.create_for_volume(synthetic_volume_full(mgs0, secondary_hosts=[mgs1]).id, name="MGS")
        fs = self._create_file_system(mgt, other)

        self.assertEqual(mgt.nids(), ((u"1.2.3.4@tcp0", u"4.3.2.1@tcp1"), (u"1.2.3.5@tcp5", u"4.3.2.2@tcp1")))
        self.assertEqual(fs.mgs_spec(), u"1.2.3.4@tcp0,4.3.2.1@tcp1:1.2.3.5@tcp5,4.3.2.2@tcp1")
