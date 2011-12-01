
from django.test import TestCase

from configure.lib.storage_plugin import attributes
from configure.lib.storage_plugin import resource_attribute


class TestAttributes(TestCase):
    def test_label(self):
        attr = resource_attribute.BaseResourceAttribute(label = 'foobar')
        self.assertEqual(attr.get_label('my_attribute'), 'foobar')

        attr = resource_attribute.BaseResourceAttribute()
        self.assertEqual(attr.get_label('my_attribute'), 'My attribute')

    def test_string(self):
        str = attributes.String(max_length = 512)
        str.validate("")
        str.validate("x" * 511)

        toolong = "x" * 513
        with self.assertRaisesRegexp(ValueError, "Value '%s' too long" % toolong):
            str.validate(toolong)

    def test_boolean(self):
        bool = attributes.Boolean()
        self.assertEqual(bool.encode(None), False)
        self.assertEqual(bool.encode(0), False)
        self.assertEqual(bool.encode(1), True)
        self.assertEqual(bool.encode(True), True)
        self.assertEqual(bool.encode(False), False)

        self.assertEqual(bool.decode(False), False)
        self.assertEqual(bool.decode(True), True)

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


class TestReferenceAttribute(TestCase):
    def setUp(self):
        import configure.lib.storage_plugin.manager
        self.original_mgr = configure.lib.storage_plugin.manager.storage_plugin_manager

        from helper import load_plugins
        mgr = load_plugins(['loadable_plugin'])
        configure.lib.storage_plugin.manager.storage_plugin_manager = mgr
        self.record_pk = mgr.create_root_resource('loadable_plugin', 'TestScannableResource', name = 'foobar')

        self.manager = mgr

    def tearDown(self):
        import configure.lib.storage_plugin.manager
        configure.lib.storage_plugin.manager.storage_plugin_manager = self.original_mgr

    def test_decode(self):
        import json
        rr = attributes.ResourceReference()
        self.assertEqual(rr.decode(json.dumps(None)), None)

        resource = rr.decode(json.dumps(self.record_pk))
        from configure.lib.storage_plugin.resource import StorageResource
        self.assertIsInstance(resource, StorageResource)

    def test_markup(self):
        import json
        rr = attributes.ResourceReference()

        self.assertEqual(rr.to_markup(None), '')

        def hyperlink_markup(id, label):
            from django.utils.html import conditional_escape
            return "<a class='storage_resource' href='#%s'>%s</a>" % (id, conditional_escape(label))

        resource = rr.decode(json.dumps(self.record_pk))
        markup = rr.to_markup(resource)
        self.assertEqual(markup, hyperlink_markup(self.record_pk, resource.human_string()))

        from configure.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk = self.record_pk)
        record.alias = 'test alias'
        record.save()

        markup = rr.to_markup(resource)
        self.assertEqual(markup, hyperlink_markup(self.record_pk, 'test alias'))

    def test_validate(self):
        import json

        rr = attributes.ResourceReference(optional = True)
        rr.validate(None)
        with self.assertRaises(ValueError):
            rr.validate("not a resource")
        resource = rr.decode(json.dumps(self.record_pk))
        rr.validate(resource)

        rr = attributes.ResourceReference()
        rr.validate(resource)
        with self.assertRaises(ValueError):
            rr.validate(None)
        with self.assertRaises(ValueError):
            rr.validate("not a resource")
