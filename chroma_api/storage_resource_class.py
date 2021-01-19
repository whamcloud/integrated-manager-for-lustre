# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.lib.storage_plugin.api import attributes

from chroma_core.models import StorageResourceClass

from tastypie import fields
from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization

from chroma_api.chroma_model_resource import ChromaModelResource


def filter_class_ids():
    """Wrapper to avoid importing storage_plugin_manager at module scope (it
    requires DB to construct itself) so that this module can be imported
    for e.g. building docs without a database.

    Return a list of storage resource class IDs which are valid for display (i.e.
    those for which we have a plugin available in this process)
    """
    from django.db.utils import DatabaseError, OperationalError

    try:
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        return storage_plugin_manager.resource_class_id_to_class.keys()
    except (OperationalError, DatabaseError):
        # OperationalError if the DB server can't be contacted
        # DatabaseError if the DB exists but isn't populated
        return []


class StorageResourceClassResource(ChromaModelResource):
    """
    Defines a type of ``storage_resource`` that can be created.

    Storage resource classes belong to a particular plugin (``plugin_name`` attribute)
    . The name of the storage resource class (``class_name`` attribute)
    is unique within the plugin.
    """

    plugin_name = fields.CharField(attribute="storage_plugin__module_name")
    plugin_internal = fields.BooleanField(attribute="storage_plugin__internal")
    label = fields.CharField(
        help_text="A unique human-readable name for the resource class, including"
        'the plugin name.  e.g. "TestPlugin-ResourceOne"'
    )
    columns = fields.ListField(
        help_text="List of resource attributes to be used when presenting resource in tabular form"
    )
    fields = fields.DictField(help_text="List of resource attributes which should be presented in an input form")

    def dehydrate_columns(self, bundle):
        properties = bundle.obj.get_class().get_all_attribute_properties()
        return [
            {"name": name, "label": props.get_label(name)}
            for (name, props) in properties
            if not isinstance(props, attributes.Password)
        ]

    def dehydrate_fields(self, bundle):
        resource_klass = bundle.obj.get_class()

        fields = []
        for name, attr in resource_klass.get_all_attribute_properties():
            fields.append(
                {
                    "label": attr.get_label(name),
                    "name": name,
                    "optional": attr.optional,
                    "user_read_only": attr.user_read_only,
                    "class": attr.__class__.__name__,
                }
            )
        return fields

    def dehydrate_label(self, bundle):
        return "%s-%s" % (bundle.obj.storage_plugin.module_name, bundle.obj.class_name)

    class Meta:
        queryset = StorageResourceClass.objects.filter(id__in=filter_class_ids())
        resource_name = "storage_resource_class"
        filtering = {
            "plugin_name": ["exact"],
            "class_name": ["exact"],
            "user_creatable": ["exact"],
            "plugin_internal": ["exact"],
        }
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        list_allowed_methods = ["get"]
        detail_allowed_methods = ["get"]
        ordering = ["class_name"]

    def prepend_urls(self):
        from django.conf.urls import url

        return [
            url(
                r"^(?P<resource_name>%s)/(?P<storage_plugin__module_name>\w+)/(?P<class_name>\w+)/$"
                % self._meta.resource_name,
                self.wrap_view("dispatch_detail"),
                name="dispatch_detail",
            )
        ]
