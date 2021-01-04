import random

from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase
from chroma_core.models import Volume
from chroma_core.services.job_scheduler.job_scheduler import JobScheduler
from tests.unit.chroma_core.helpers.synthentic_objects import synthetic_host, synthetic_volume_full
from tests.unit.chroma_core.helpers.helper import load_default_profile


class TestOrderedTargets(IMLUnitTestCase):
    """Check that the target ordering works correctly across volumes"""

    def setUp(self):
        super(TestOrderedTargets, self).setUp()

        # If the test that just ran imported storage_plugin_manager, it will
        # have instantiated its singleton, and created some DB records.
        # Django TestCase rolls back the database, so make sure that we
        # also roll back (reset) this singleton.
        import chroma_core.lib.storage_plugin.manager

        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = (
            chroma_core.lib.storage_plugin.manager.StoragePluginManager()
        )

        load_default_profile()

        self.job_scheduler = JobScheduler()
        self.no_of_nodes = 10
        self.nodes = []

        for node in range(0, self.no_of_nodes):
            self.nodes.append(synthetic_host("node%s" % node))

        for node in self.nodes:
            synthetic_volume_full(node, secondary_hosts=list(set(self.nodes) - set([node])))

        self.volume_ids = [volume.id for volume in Volume.objects.all()]

    def test_ordered_single(self):
        result = self.job_scheduler.order_targets([{"volume_id": volume.id} for volume in Volume.objects.filter()])

        self.assertEqual(len(result), len(self.nodes))

        for index, volume in enumerate(result):
            self.assertEqual(volume["index"], 0)
            self.assertEqual(volume["volume_id"], self.volume_ids[index])

    def test_ordered_multiple(self):
        # Create three times the id.
        mdt_data = []

        for i in range(0, 3):
            mdt_data += [{"volume_id": volume.id} for volume in Volume.objects.filter()]

        result = self.job_scheduler.order_targets(mdt_data)

        self.assertEqual(len(result), len(self.nodes) * 3)

        for index, volume in enumerate(result):
            self.assertEqual(volume["index"], index / self.no_of_nodes)
            self.assertEqual(volume["volume_id"], self.volume_ids[index % self.no_of_nodes])

    def test_random(self):
        # Jumble them up. The randomness isn't important just the fact they are out of order.
        random_volumes = sorted(
            [{"volume_id": volume.id} for volume in Volume.objects.filter()], key=lambda arg: random.random()
        )

        result = self.job_scheduler.order_targets(random_volumes)

        self.assertEqual(len(result), len(self.nodes))

        for index, volume in enumerate(result):
            self.assertEqual(volume["index"], 0)
            self.assertEqual(volume["volume_id"], random_volumes[index]["volume_id"])

    def test_mdt_root(self):
        # With a root defined for one of the elements it should move to the beginning
        volumes = [{"volume_id": volume.id} for volume in Volume.objects.filter()]
        volumes[self.no_of_nodes / 2]["root"] = True

        result = self.job_scheduler.order_targets(volumes)

        self.assertEqual(len(result), len(self.nodes))

        # Now do the reorder we expect
        volumes.insert(0, volumes.pop(self.no_of_nodes / 2))

        for index, volume in enumerate(result):
            self.assertEqual(volume["index"], 0)
            self.assertEqual(volume["volume_id"], volumes[index]["volume_id"])
