
from django.test import TestCase
from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource


class TestDefaults1(BaseStorageResource):
    class Meta:
        identifier = GlobalId('name')

    name = attributes.String()


class TestDefaults2(BaseStorageResource):
    class Meta:
        identifier = GlobalId('name', 'name_scope')

    name = attributes.String()
    name_scope = attributes.String()
    read = statistics.Gauge()
    write = statistics.Gauge()


class TestOverrides(BaseStorageResource):
    class Meta:
        identifier = GlobalId('name')
        label = "Alpha"
        charts = [{'title': 'IO', 'series': ['read', 'write']}]

    def get_label(self):
        return "Bravo"

    name = attributes.String()
    read = statistics.Gauge()
    write = statistics.Gauge()


class TestDisplayNames(TestCase):
    def test_defaults(self):
        td1 = TestDefaults1(name = "foo")
        self.assertEqual(td1.get_label(), "TestDefaults1 foo")

        td2 = TestDefaults2(name = "foo", name_scope = "bar")
        self.assertEqual(td2.get_label(), "TestDefaults2 ('foo', 'bar')")
        self.assertEqual(len(td2.get_charts()), 2)

    def test_overrides(self):
        to = TestOverrides(name = "foo")
        self.assertEqual(to.get_label(), "Bravo")
        self.assertEqual(to._meta.label, "Alpha")
        self.assertEqual(len(to.get_charts()), 1)
