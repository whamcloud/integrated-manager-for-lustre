#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.contrib.contenttypes.models import ContentType
from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource

from chroma_core.models import StorageResourceRecord, StorageResourceStatistic

from tastypie.authorization import DjangoAuthorization
from chroma_api.authentication import AnonymousAuthentication
from tastypie.resources import ModelResource
from tastypie import fields
from chroma_core.lib.storage_plugin.query import ResourceQuery
from chroma_api.utils import MetricResource

from tastypie.exceptions import NotFound, ImmediateHttpResponse
from tastypie import http
from django.core.exceptions import ObjectDoesNotExist

from chroma_api.storage_resource_class import filter_class_ids

from chroma_core.lib.storage_plugin.daemon import ScanDaemonRpc


class StorageResourceResource(MetricResource, ModelResource):
    """
    Storage resources are objects within Chroma's storage plugin
    framework.  Note: the term 'resource' is overloaded, used
    both in the API and in the storage plugin framework.

    A storage resource is of a class defined by the
    ``storage_resource_class`` resource.

    This resource has a special ancestor_of filter argument, which may be set to
    the ID of a storage resource to retrieve all resources which its ancestors.
    """
    #FIXME: document this fully when the storage plugin API freezes

    content_type_id = fields.IntegerField()
    attributes = fields.DictField()
    alias = fields.CharField()

    alerts = fields.ListField()
    stats = fields.DictField()
    charts = fields.ListField()
    propagated_alerts = fields.ListField()

    default_alias = fields.CharField()

    plugin_name = fields.CharField(attribute='resource_class__storage_plugin__module_name')
    class_name = fields.CharField(attribute='resource_class__class_name')

    parent_classes = fields.ListField(blank = True, null = True)

    deletable = fields.BooleanField()

    def dehydrate_parent_classes(self, bundle):
        def find_bases(klass, bases = set()):
            for parent in klass.__bases__:
                if issubclass(parent, BaseStorageResource):
                    bases.add(parent)
                    bases |= find_bases(parent, bases)

            return bases

        return [k.__name__ for k in find_bases(bundle.obj.resource_class.get_class())]

    def obj_get_list(self, request = None, **kwargs):
        """Override this to do sorting in a way that depends on kwargs (we need
        to know what kind of object is being listed in order to resolve the
        ordering attribute to a model, and apply_sorting's arguments don't
        give you kwargs)"""
        objs = super(StorageResourceResource, self).obj_get_list(request, **kwargs)
        objs = self._sort_by_attr(objs, request.GET, **kwargs)
        return objs

    def get_list(self, request, **kwargs):
        if 'ancestor_of' in request.GET:
            record = StorageResourceRecord.objects.get(id = request.GET['ancestor_of'])
            ancestor_records = set(ResourceQuery().record_all_ancestors(record))

            bundles = [self.build_bundle(obj=obj, request=request) for obj in ancestor_records]
            dicts = [self.full_dehydrate(bundle) for bundle in bundles]
            return self.create_response(request, {"meta": None, "objects": dicts})
        else:
            return super(StorageResourceResource, self).get_list(request, **kwargs)

    def _sort_by_attr(self, obj_list, options = None, **kwargs):
        options = options or {}
        order_by = options.get('order_by', None)
        if not order_by:
            return obj_list

        if order_by.find('attr_') == 0:
            attr_name = order_by[5:]
            invert = False
        elif order_by.find('attr_') == 1:
            attr_name = order_by[6:]
            invert = True
        else:
            raise RuntimeError("Can't sort on %s" % order_by)

        try:
            class_name = kwargs['class_name']
            plugin_name = kwargs['plugin_name']
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

    def dehydrate_stats(self, bundle):
        from chroma_core.models import SimpleHistoStoreTime
        from chroma_core.models import SimpleHistoStoreBin
        stats = {}
        for s in StorageResourceStatistic.objects.filter(storage_resource = bundle.obj):
            from django.db import transaction
            stat_props = s.storage_resource.get_statistic_properties(s.name)
            if isinstance(stat_props, statistics.BytesHistogram):
                with transaction.commit_manually():
                    transaction.commit()
                    try:
                        time = SimpleHistoStoreTime.objects.filter(storage_resource_statistic = s).latest('time')
                        bins = SimpleHistoStoreBin.objects.filter(histo_store_time = time).order_by('bin_idx')
                    finally:
                        transaction.commit()
                type_name = 'histogram'
                # Composite type
                data = {'bin_labels': [], 'values': []}
                for i in range(0, len(stat_props.bins)):
                    bin_info = u"\u2264%s" % stat_props.bins[i][1]
                    data['bin_labels'].append(bin_info)
                    data['values'].append(bins[i].value)
            else:
                type_name = 'timeseries'
                # Go get the data from <resource>/metrics/
                data = None

            label = stat_props.label
            if not label:
                label = s.name

            stat_data = {'name': s.name,
                    'label': label,
                    'type': type_name,
                    'unit_name': stat_props.get_unit_name(),
                    'data': data}
            stats[s.name] = stat_data

        return stats

    def dehydrate_charts(self, bundle):
        return bundle.obj.to_resource().get_charts()

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
                    raw = api.get_resource_uri(StorageResourceRecord.objects.get(pk = val._handle))
                else:
                    raw = None
            else:
                raw = val
            result[name] = {
                'raw': raw,
                'markup': props.to_markup(val),
                'label': props.get_label(name),
                'class': props.__class__.__name__}
        return result

    class Meta:
        queryset = StorageResourceRecord.objects.filter(resource_class__id__in = filter_class_ids())
        resource_name = 'storage_resource'
        #filtering = {'storage_plugin__module_name': ['exact'], 'class_name': ['exact']}
        filtering = {'class_name': ['exact'], 'plugin_name': ['exact']}
        authorization = DjangoAuthorization()
        authentication = AnonymousAuthentication()
        always_return_data = True

    def obj_delete(self, request = None, **kwargs):
        try:
            obj = self.obj_get(request, **kwargs)
        except ObjectDoesNotExist:
            raise NotFound("A model instance matching the provided arguments could not be found.")

        ScanDaemonRpc().remove_resource(obj.id)
        raise ImmediateHttpResponse(http.HttpAccepted())

    def obj_create(self, bundle, request = None, **kwargs):
        # Note: not importing this at module scope so that this module can
        # be imported without loading plugins (useful at installation)
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(bundle.data['plugin_name'], bundle.data['class_name'])
        attrs = {}
        input_attrs = bundle.data['attrs']
        for name, properties in resource_class.get_all_attribute_properties():
            if isinstance(properties, attributes.Password) and name in input_attrs:
                attrs[name] = properties.encrypt(input_attrs[name])
            elif name in input_attrs:
                attrs[name] = input_attrs[name]
            elif not properties.optional:
                # TODO: proper validation
                raise RuntimeError("%s not optional" % name)

        # Construct a record
        record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, attrs)
        #record_dict = self.full_dehydrate(self.build_bundle(obj = record)).data
        bundle.obj = record

        return bundle

    def obj_update(self, bundle, request = None, **kwargs):
        bundle.obj = self.cached_obj_get(request = request, **self.remove_api_resource_names(kwargs))

        if 'alias' in bundle.data:
            # FIXME: sanitize input for alias (it gets echoed back as markup)
            alias = bundle.data['alias']
            record = bundle.obj
            if alias == "":
                record.alias = None
            else:
                record.alias = alias
            record.save()

        input_attrs = bundle.data
        attrs = {}
        resource_class = record.resource_class.get_class()
        for name, properties in resource_class.get_all_attribute_properties():
            if name in bundle.data:
                if isinstance(properties, attributes.Password):
                    attrs[name] = properties.encrypt(input_attrs[name])
                else:
                    attrs[name] = input_attrs[name]

        if len(attrs):
            # NB this operation is done inside the storage daemon, because it is
            # necessary to tear down any running session (e.g. consider modifying the IP
            # address of a controller)
            ScanDaemonRpc().modify_resource(record.id, attrs)

        # Require that something was set
        if not 'alias' in bundle.data or len(attrs):
            raise ImmediateHttpResponse(http.HttpBadRequest())

        return bundle

    def override_urls(self):
        from django.conf.urls.defaults import url
        return super(StorageResourceResource, self).override_urls() + [
            url(r"^(?P<resource_name>%s)/(?P<plugin_name>\D\w+)/(?P<class_name>\D\w+)/$" % self._meta.resource_name, self.wrap_view('dispatch_list'), name="dispatch_list"),
]
