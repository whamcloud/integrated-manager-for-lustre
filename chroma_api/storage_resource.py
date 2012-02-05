#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.contrib.contenttypes.models import ContentType

from requesthandler import AnonymousRESTRequestHandler
from hydraapi.requesthandler import APIResponse

from configure.models import StorageResourceRecord
from configure.lib.storage_plugin.manager import storage_plugin_manager
from django.shortcuts import get_object_or_404


class StorageResourceHandler(AnonymousRESTRequestHandler):
    def put(self, request, id):
        # request.data should be a dict representing updated
        # fields for the resource

        # We only support updating the 'alias' field
        assert 'alias' in request.data
        alias = request.data['alias']

        record = get_object_or_404(StorageResourceRecord, id = id)
        if alias == "":
            record.alias = None
        else:
            record.alias = alias
        record.save()

        return APIResponse(None, 204)

    def post(self, request, module_name, class_name):
        # request.data should be a dict representing the resource attributes
        attributes = request.data

        record = storage_plugin_manager.create_root_resource(module_name, class_name, **attributes)
        return record.to_dict()

    def remove(self, request, id):
        from configure.lib.storage_plugin.daemon import StorageDaemon
        StorageDaemon.request_remove_resource(id)
        # TODO: make the request to remove the resource something that
        # we can track (right now it's a "hope for the best")
        return APIResponse(None, 202)

    def get(self, request, id = None, module_name = None, class_name = None):
        # FIXME: the plural version is returning a form which is
        # specific to datatables, it should either be respecting a
        # format flag or returning vanilla output for client side conversion
        if module_name and class_name:
            resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(module_name, class_name)
            attr_columns = resource_class.get_columns()

            rows = []
            from django.utils.html import conditional_escape
            from configure.lib.storage_plugin.query import ResourceQuery
            for record in ResourceQuery().get_class_resources(resource_class_id):
                resource = record.to_resource()
                alias = conditional_escape(record.alias_or_name(resource))
                alias_markup = "<a class='storage_resource' href='#%s'>%s</a>" % (record.pk, alias)

                # NB What we output here is logically markup, not strings, so we escape.
                # (underlying storage_plugin.attributes do their own escaping
                row = {
                        'id': record.pk,
                        'content_type_id': ContentType.objects.get_for_model(record).id,
                        '_alias': alias_markup,
                        0: 'wtf'
                        }
                for c in attr_columns:
                    row[c['name']] = resource.format(c['name'])

                row['_alerts'] = [a.to_dict() for a in ResourceQuery().resource_get_alerts(resource)]

                rows.append(row)

            columns = [{'mdataProp': 'id', 'bVisible': False}, {'mDataProp': '_alias', 'sTitle': 'Name'}]
            for c in attr_columns:
                columns.append({'sTitle': c['label'], 'mDataProp': c['name']})
            return {'aaData': rows, 'aoColumns': columns}
        elif id:
            record = get_object_or_404(StorageResourceRecord, id = id)
            return record.to_dict()
