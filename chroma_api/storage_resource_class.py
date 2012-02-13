#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import StorageResourceClass

from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from tastypie.resources import ModelResource


class StorageResourceClassResource(ModelResource):
    plugin_name = fields.CharField(attribute='storage_plugin__module_name')
    columns = fields.ListField()
    label = fields.CharField()
    fields = fields.DictField()

    def dehydrate_columns(self, bundle):
        return bundle.obj.get_class().get_columns()
        #columns = [{'mdataProp': 'id', 'bVisible': False}, {'mDataProp': '_alias', 'sTitle': 'Name'}]
        #for c in attr_columns:
        #    columns.append({'sTitle': c['label'], 'mDataProp': c['name']})
        #return columns

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
        queryset = StorageResourceClass.objects.all()
        resource_name = 'storage_resource_class'
        filtering = {'plugin_name': ['exact'], 'class_name': ['exact'], 'user_creatable': ['exact']}
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        ordering = ['class_name']

    def override_urls(self):
        from django.conf.urls.defaults import url
        return [
            url(r"^(?P<resource_name>%s)/(?P<storage_plugin__module_name>\w+)/(?P<class_name>\w+)/$" % self._meta.resource_name, self.wrap_view('dispatch_detail'), name="dispatch_detail"),
]
