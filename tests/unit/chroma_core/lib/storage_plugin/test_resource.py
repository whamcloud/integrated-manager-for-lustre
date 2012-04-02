
from django.test import TestCase
from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource


class TestDefaults1(BaseStorageResource):
    name = attributes.String()
    identifier = GlobalId('name')


class TestDefaults2(BaseStorageResource):
    name = attributes.String()
    name_scope = attributes.String()
    identifier = GlobalId('name', 'name_scope')


class TestOverrides(BaseStorageResource):
    name = attributes.String()
    identifier = GlobalId('name')

    class_label = "Alpha"

    def get_label(self):
        return "Bravo"


class TestDisplayNames(TestCase):
    def test_defaults(self):
        td1 = TestDefaults1(name = "foo")
        self.assertEqual(td1.get_label(), "TestDefaults1 foo")

        td2 = TestDefaults2(name = "foo", name_scope = "bar")
        self.assertEqual(td2.get_label(), "TestDefaults2 ('foo', 'bar')")

    def test_overrides(self):
        to = TestOverrides(name = "foo")
        self.assertEqual(to.get_label(), "Bravo")
        self.assertEqual(to.get_class_label(), "Alpha")
