# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import defaultdict
from django.contrib.contenttypes.models import ContentType
from tastypie.validation import Validation
from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource

from chroma_core.models import StorageResourceRecord

from chroma_api.authentication import AnonymousAuthentication, PatchedDjangoAuthorization
from tastypie import fields
from chroma_core.lib.storage_plugin.query import ResourceQuery
from chroma_api.validation_utils import validate

from tastypie.exceptions import NotFound, ImmediateHttpResponse
from tastypie import http
from django.core.exceptions import ObjectDoesNotExist

from chroma_api.storage_resource_class import filter_class_ids
from chroma_api.chroma_model_resource import ChromaModelResource


from chroma_core.services.plugin_runner.scan_daemon_interface import ScanDaemonRpcInterface


class StorageResourceValidation(Validation):
    def is_valid(self, bundle, request=None):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        from chroma_core.lib.storage_plugin.manager import PluginNotFound

        errors = defaultdict(list)
        if "alias" in bundle.data and bundle.data["alias"] is not None:
            alias = bundle.data["alias"]
            if alias.strip() == "":
                errors["alias"].append("May not be blank")
            elif alias != alias.strip():
                errors["alias"].append("No trailing whitespace allowed")

        if "plugin_name" in bundle.data:
            try:
                storage_plugin_manager.get_plugin_class(bundle.data["plugin_name"])
            except PluginNotFound as e:
                errors["plugin_name"].append(e.__str__())
            else:
                if "class_name" in bundle.data:
                    try:
                        storage_plugin_manager.get_plugin_resource_class(
                            bundle.data["plugin_name"], bundle.data["class_name"]
                        )
                    except PluginNotFound as e:
                        errors["class_name"].append(e.__str__())

        return errors


class StorageResourceResource(ChromaModelResource):
    """
    Storage resources are objects within the storage plugin
    framework.  Note: the term 'resource' is used to refer to
    REST API resources and also in this context to refer to the
    separate concept of a storage resource.

    A storage resource is of a class defined by the
    ``storage_resource_class`` resource.

    This resource has a special ``ancestor_of`` filter argument, which may be set to
    the ID of a storage resource to retrieve all the resources that are its ancestors.
    """

    # FIXME: document this fully when the storage plugin API freezes

    attributes = fields.DictField(help_text="Dictionary of attributes as defined by the storage plugin")
    alias = fields.CharField(help_text="The human readable name of the resource (may be set by user)")

    alerts = fields.ListField(help_text="List of active ``alert`` objects which are associated with this resource")
    propagated_alerts = fields.ListField(
        help_text="List of active ``alert`` objects which are associated with " "ancestors of this resource"
    )

    default_alias = fields.CharField(help_text="The default human readable name of the resource")

    plugin_name = fields.CharField(
        attribute="resource_class__storage_plugin__module_name",
        help_text="Name of the storage plugin which defines this resource",
    )
    class_name = fields.CharField(
        attribute="resource_class__class_name", help_text="Name of a ``storage_resource_class``"
    )

    parent_classes = fields.ListField(
        blank=True, null=True, help_text="List of strings, parent classes of" "this object's class."
    )

    deletable = fields.BooleanField(help_text="If ``true``, this object may be removed with a DELETE operation")

    def dehydrate_parent_classes(self, bundle):
        def find_bases(klass, bases=set()):
            for parent in klass.__bases__:
                if issubclass(parent, BaseStorageResource):
                    bases.add(parent)
                    bases |= find_bases(parent, bases)

            return bases

        return [k.__name__ for k in find_bases(bundle.obj.resource_class.get_class())].sort()

    def obj_get_list(self, bundle, **kwargs):
        """Override this to do sorting in a way that depends on kwargs (we need
        to know what kind of object is being listed in order to resolve the
        ordering attribute to a model, and apply_sorting's arguments don't
        give you kwargs)"""
        objs = super(StorageResourceResource, self).obj_get_list(bundle, **kwargs)
        objs = self._sort_by_attr(objs, bundle.request.GET, **kwargs)
        return objs

    def get_list(self, request, **kwargs):
        if "ancestor_of" in request.GET:
            record = StorageResourceRecord.objects.get(id=request.GET["ancestor_of"])
            ancestor_records = set(ResourceQuery().record_all_ancestors(record))

            bundles = [self.build_bundle(obj=obj, request=request) for obj in ancestor_records]
            dicts = [self.full_dehydrate(bundle) for bundle in bundles]
            return self.create_response(request, {"meta": None, "objects": dicts})
        else:
            return super(StorageResourceResource, self).get_list(request, **kwargs)

    def _sort_by_attr(self, obj_list, options=None, **kwargs):
        options = options or {}
        order_by = options.get("order_by", None)
        if not order_by:
            return obj_list

        if order_by.find("attr_") == 0:
            attr_name = order_by[5:]
            invert = False
        elif order_by.find("attr_") == 1:
            attr_name = order_by[6:]
            invert = True
        else:
            raise RuntimeError("Can't sort on %s" % order_by)

        try:
            class_name = kwargs["class_name"]
            plugin_name = kwargs["plugin_name"]
        except KeyError:
            return obj_list
        else:
            from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

            klass, klass_id = storage_plugin_manager.get_plugin_resource_class(plugin_name, class_name)
            model_klass = klass.attr_model_class(attr_name)

            filter_args = {model_klass.__name__.lower() + "__key": attr_name}
            order_attr = model_klass.__name__.lower() + "__value"

            return obj_list.filter(**filter_args).order_by(("-" if invert else "") + order_attr)

    def apply_sorting(self, obj_list, options=None):
        """Pass-through in favour of sorting done in obj_get_list"""
        return obj_list

    def dehydrate_propagated_alerts(self, bundle):
        return [a.to_dict() for a in ResourceQuery().resource_get_propagated_alerts(bundle.obj.to_resource())]

    def dehydrate_deletable(self, bundle):
        return bundle.obj.resource_class.user_creatable

    def dehydrate_default_alias(self, bundle):
        return bundle.obj.to_resource().get_label()

    def dehydrate_alias(self, bundle):
        resource = bundle.obj.to_resource()
        return bundle.obj.alias_or_name(resource)

    def dehydrate_alerts(self, bundle):
        return [a.to_dict() for a in ResourceQuery().resource_get_alerts(bundle.obj.to_resource())]

    def dehydrate_content_type_id(self, bundle):
        return ContentType.objects.get_for_model(bundle.obj.__class__).pk

    def dehydrate_attributes(self, bundle):
        # a list of dicts, one for each attribute.  Excludes hidden attributes.
        result = {}
        resource = bundle.obj.to_resource()
        attr_props = resource.get_all_attribute_properties()
        for name, props in attr_props:
            # Exclude password hashes
            if isinstance(props, attributes.Password):
                continue

            val = getattr(resource, name)
            if isinstance(val, BaseStorageResource):
                if val._handle:
                    from chroma_api.urls import api

                    raw = api.get_resource_uri(StorageResourceRecord.objects.get(pk=val._handle))
                else:
                    raw = None
            else:
                raw = val
            result[name] = {
                "raw": raw,
                "markup": props.to_markup(val),
                "label": props.get_label(name),
                "class": props.__class__.__name__,
            }
        return result

    class Meta:
        queryset = StorageResourceRecord.objects.filter(resource_class__id__in=filter_class_ids())
        resource_name = "storage_resource"
        filtering = {"class_name": ["exact"], "plugin_name": ["exact"]}
        authorization = PatchedDjangoAuthorization()
        authentication = AnonymousAuthentication()
        always_return_data = True
        validation = StorageResourceValidation()

    def obj_delete(self, bundle, **kwargs):
        try:
            obj = self.obj_get(bundle, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")

        ScanDaemonRpcInterface().remove_resource(obj.id)
        raise ImmediateHttpResponse(http.HttpAccepted())

    @validate
    def obj_create(self, bundle, **kwargs):
        # Note: not importing this at module scope so that this module can
        # be imported without loading plugins (useful at installation)
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(
            bundle.data["plugin_name"], bundle.data["class_name"]
        )
        attrs = {}
        input_attrs = bundle.data["attrs"]
        for name, property in resource_class.get_all_attribute_properties():
            if name in input_attrs:
                attrs[name] = property.encrypt(property.cast(input_attrs[name]))
            elif property.default:
                attrs[name] = property.default
            elif not property.optional:
                # TODO: proper validation
                raise RuntimeError("%s not optional" % name)

        # Construct a record
        record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, attrs)
        # record_dict = self.full_dehydrate(self.build_bundle(obj = record)).data
        bundle.obj = record

        return bundle

    @validate
    def obj_update(self, bundle, **kwargs):
        bundle.obj = self.cached_obj_get(bundle, **self.remove_api_resource_names(kwargs))

        if "alias" in bundle.data:
            # FIXME: sanitize input for alias (it gets echoed back as markup)
            alias = bundle.data["alias"]
            record = bundle.obj
            if alias == "":
                record.alias = None
            else:
                record.alias = alias
            record.save()

        input_attrs = bundle.data
        attrs = {}
        resource_class = record.resource_class.get_class()
        for name, property in resource_class.get_all_attribute_properties():
            if name in bundle.data:
                attrs[name] = property.encrypt(property.cast(input_attrs[name]))

        if len(attrs):
            # NB this operation is done inside the storage daemon, because it is
            # necessary to tear down any running session (e.g. consider modifying the IP
            # address of a controller)
            ScanDaemonRpcInterface().modify_resource(record.id, attrs)

        # Require that something was set
        if not "alias" in bundle.data or len(attrs):
            raise ImmediateHttpResponse(http.HttpBadRequest())

        return bundle

    def prepend_urls(self):
        from django.conf.urls import url

        return super(StorageResourceResource, self).prepend_urls() + [
            url(
                r"^(?P<resource_name>%s)/(?P<plugin_name>\D\w+)/(?P<class_name>\D\w+)/$" % self._meta.resource_name,
                self.wrap_view("dispatch_list"),
                name="dispatch_list",
            )
        ]
