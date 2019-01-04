from django.db.models.query_utils import Q

from chroma_core.models.storage_plugin import StorageResourceRecord
from tests.unit.chroma_core.lib.storage_plugin.resource_manager.test_resource_manager import ResourceManagerTestCase


class TestEdgeIndex(ResourceManagerTestCase):
    def setUp(self):
        super(TestEdgeIndex, self).setUp("example_plugin")

    def test_add_remove(self):
        from chroma_core.services.plugin_runner.resource_manager import EdgeIndex

        index = EdgeIndex()
        child = 1
        parent = 2
        index.add_parent(child, parent)
        self.assertEqual(index.get_parents(child), [parent])
        self.assertEqual(index.get_children(parent), [child])
        index.remove_parent(child, parent)
        self.assertEqual(index.get_parents(child), ([]))
        self.assertEqual(index.get_children(parent), ([]))

        index.add_parent(child, parent)
        index.remove_node(parent)
        self.assertEqual(index.get_parents(child), ([]))
        self.assertEqual(index.get_children(parent), ([]))

        index.add_parent(child, parent)
        index.remove_node(child)
        self.assertEqual(index.get_parents(child), ([]))
        self.assertEqual(index.get_children(parent), ([]))

    def test_populate(self):
        from chroma_core.services.plugin_runner.resource_manager import EdgeIndex

        resource_record, couplet_resource = self._make_global_resource(
            "example_plugin", "Couplet", {"address_1": "foo", "address_2": "bar"}
        )
        controller_resource = self._make_local_resource(
            "example_plugin", "Controller", index=0, parents=[couplet_resource]
        )

        self.resource_manager.session_open(self.plugin, resource_record.pk, [couplet_resource, controller_resource], 60)

        # By not fetching the Couple and not fetching the plugin we should be left with 1 entry, this will raise an exception if the
        # result is not 1 entry.
        controller_record = StorageResourceRecord.objects.get(
            ~Q(id=resource_record.pk), ~Q(id=self.plugin._scannable_id)
        )

        index = EdgeIndex()
        index.populate()
        self.assertEqual(index.get_parents(controller_record.pk), [resource_record.pk])
        self.assertEqual(index.get_children(resource_record.pk), [controller_record.pk])
