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
