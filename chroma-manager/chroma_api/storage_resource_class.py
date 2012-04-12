#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================
from tastypie.constants import ALL
from chroma_core.lib.storage_plugin.api import attributes

from chroma_core.models import StorageResourceClass

from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from tastypie.resources import ModelResource


def filter_class_ids():
    """Wrapper to avoid importing storage_plugin_manager at module scope (it
    requires DB to construct itself) so that this module can be imported
    for e.g. building docs without a database.

    Return a list of storage resource class IDs which are valid for display (i.e.
    those for which we have a plugin available in this process)
    """
    from MySQLdb import OperationalError
    try:
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        return storage_plugin_manager.resource_class_id_to_class.keys()
    except OperationalError:
        return []


class StorageResourceClassResource(ModelResource):
    """
    A type of ``storage_resource`` which may be created.

    Storage resource classes belong to a particular plugin (``plugin_name``)
    attribute.  The name (``class_name``) is unique within that plugin
    They provide the ``columns`` attribute to suggest which
    resource attributes should be displayed in a tabular view, and the
    ``fields`` attribute to describe the resource class's attributes in
    enough to detail to present an input form.

    The ``label`` attribute is a presentation helper which gives
    a plugin-qualified name like "TestPlugin-ResourceOne".
    """
    plugin_name = fields.CharField(attribute='storage_plugin__module_name')
    plugin_internal = fields.BooleanField(attribute='storage_plugin__internal')
    columns = fields.ListField()
    label = fields.CharField()
    fields = fields.DictField()

    def dehydrate_columns(self, bundle):
        properties = bundle.obj.get_class().get_all_attribute_properties()
        return [{'name': name, 'label': props.get_label(name)} for (name, props) in properties if not isinstance(props, attributes.Password)]

    def dehydrate_fields(self, bundle):
        resource_klass = bundle.obj.get_class()

        fields = []
        for name, attr in resource_klass.get_all_attribute_properties():
            fields.append({
                'label': attr.get_label(name),
                'name': name,
                'optional': attr.optional,
                'class': attr.__class__.__name__})
        return fields

    def dehydrate_label(self, bundle):
        return "%s-%s" % (bundle.obj.storage_plugin.module_name, bundle.obj.class_name)

    class Meta:
        queryset = StorageResourceClass.objects.filter(
                id__in = filter_class_ids())
        resource_name = 'storage_resource_class'
        filtering = {
            'plugin_name': ['exact'],
            'class_name': ['exact'],
            'user_creatable': ['exact'],
            'plugin_internal': ['exact']}
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        ordering = ['class_name']

    def override_urls(self):
        from django.conf.urls.defaults import url
        return [
            url(r"^(?P<resource_name>%s)/(?P<storage_plugin__module_name>\w+)/(?P<class_name>\w+)/$" % self._meta.resource_name, self.wrap_view('dispatch_detail'), name="dispatch_detail"),
]
