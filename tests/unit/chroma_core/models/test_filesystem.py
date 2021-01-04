import mock

from chroma_core.models import ManagedHost, Nid
from tests.unit.chroma_core.helpers.synthentic_objects import synthetic_host
from tests.unit.chroma_core.helpers.helper import create_simple_fs, load_default_profile
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

        def get_targets_fn():
            ids = [x.id for x in ManagedHost.objects.all()]
            host_id = ids[0]

            return [
                {"name": "MGS", "active_host_id": host_id, "host_ids": [ids[0]]},
                {"name": "MGS_ha", "active_host_id": host_id, "host_ids": [ids[0], ids[1]]},
            ]

        self.get_targets_mock = mock.MagicMock(side_effect=get_targets_fn)
        mock.patch("chroma_core.lib.graphql.get_targets", new=self.get_targets_mock).start()

        (mgt, fs, mdt, ost) = create_simple_fs()
        self.mgt = mgt
        self.fs = fs

    def _host_with_nids(self, address):
        host_nids = {
            "primary-mgs": [Nid.Nid("1.2.3.4", "tcp", 0)],
            "failover-mgs": [Nid.Nid("1.2.3.5", "tcp", 5)],
            "primary-mgs-twonid": [Nid.Nid("1.2.3.4", "tcp", 0), Nid.Nid("4.3.2.1", "tcp", 1)],
            "failover-mgs-twonid": [Nid.Nid("1.2.3.5", "tcp", 5), Nid.Nid("4.3.2.2", "tcp", 1)],
            "othernode": [Nid.Nid("1.2.3.6", "tcp", 0), Nid.Nid("4.3.2.3", "tcp", 1)],
        }
        return synthetic_host(address, host_nids[address])
