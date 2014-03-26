
from tests.unit.chroma_core.lib.storage_plugin.helper import load_plugins

from django.test import TestCase
from django.utils.html import conditional_escape

from chroma_core.lib.storage_plugin import base_resource_attribute
from chroma_core.lib.storage_plugin.api import attributes


class TestAttributes(TestCase):
    def test_label(self):
        attr = base_resource_attribute.BaseResourceAttribute(label = 'foobar')
        self.assertEqual(attr.get_label('my_attribute'), 'foobar')

        attr = base_resource_attribute.BaseResourceAttribute()
        self.assertEqual(attr.get_label('my_attribute'), 'My attribute')

    def test_string(self):
        str = attributes.String(max_length = 512)
        str.validate("")
        str.validate("x" * 511)

        toolong = "x" * 513
        with self.assertRaisesRegexp(ValueError, "Value '%s' too long" % toolong):
            str.validate(toolong)

    def test_integer_nolimits(self):
        i = attributes.Integer()
        i.validate(-1000)
        i.validate(1024 * 1024 * 1024)
        i.validate(0)

    def test_integer_limits(self):
        i = attributes.Integer(min_val = 10, max_val = 20)
        i.validate(15)
        with self.assertRaisesRegexp(ValueError, "Value 5 too low"):
            i.validate(5)
        with self.assertRaisesRegexp(ValueError, "Value 22 too high"):
            i.validate(22)

    def test_bytes(self):
        b = attributes.Bytes()
        self.assertEqual(b.to_markup(1024), "1.0KB")
        # NB no more thorough checks here because it's just a call through to sizeof_fmt

    def test_enum(self):
        e = attributes.Enum('alpha', 'bravo')
        e.validate('alpha')
        e.validate('bravo')
        with self.assertRaises(ValueError):
            e.validate('charlie')
        with self.assertRaises(ValueError):
            e.validate('')
        with self.assertRaises(ValueError):
            e.validate(None)

        with self.assertRaises(ValueError):
            e = attributes.Enum()

    def test_uuid(self):
        u = attributes.Uuid()
        u.validate('BACBE363-A1D4-4C1A-9A08-5B47DE17AB73')
        u.validate('BACBE363A1D44C1A9A085B47DE17AB73')
        with self.assertRaises(ValueError):
            u.validate('deadbeef')

    def test_hostname(self):
        attr = attributes.Hostname()
        for value in ('intel.com', '127.0.0.1', 'my-laptop'):
            attr.validate(value)
        for value in ('intel.-com', 'my_laptop', 'x.' * 128, 'x' * 64):
            with self.assertRaises(ValueError):
                attr.validate(value)


class TestReferenceAttribute(TestCase):
    def setUp(self):
        import chroma_core.lib.storage_plugin.manager
        self.original_mgr = chroma_core.lib.storage_plugin.manager.storage_plugin_manager

        mgr = load_plugins(['loadable_plugin'])
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = mgr

        from chroma_core.models import StorageResourceRecord
        resource_class, resource_class_id = mgr.get_plugin_resource_class('loadable_plugin', 'TestScannableResource')
        record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, {'name': 'foobar'})
        self.record_pk = record.pk

        self.manager = mgr

    def tearDown(self):
        import chroma_core.lib.storage_plugin.manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.original_mgr

    def test_markup(self):
        rr = attributes.ResourceReference()

        self.assertEqual(rr.to_markup(None), '')

        from chroma_core.models import StorageResourceRecord
        resource = StorageResourceRecord.objects.get(id = self.record_pk).to_resource()
        markup = rr.to_markup(resource)
        self.assertEqual(markup, conditional_escape(resource.get_label()))

        record = StorageResourceRecord.objects.get(pk = self.record_pk)
        record.alias = 'test alias'
        record.save()

        markup = rr.to_markup(resource)
        self.assertEqual(markup, conditional_escape('test alias'))

    def test_validate(self):
        rr = attributes.ResourceReference(optional = True)
        rr.validate(None)
        with self.assertRaises(ValueError):
            rr.validate("not a resource")

        from chroma_core.models import StorageResourceRecord
        resource = StorageResourceRecord.objects.get(id = self.record_pk).to_resource()
        rr.validate(resource)

        rr = attributes.ResourceReference()
        rr.validate(resource)
        with self.assertRaises(ValueError):
            rr.validate(None)
        with self.assertRaises(ValueError):
            rr.validate("not a resource")
