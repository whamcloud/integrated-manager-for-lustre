# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.models import StorageResourceRecord
from chroma_core.lib.storage_plugin.log import storage_plugin_log

from django.db import transaction


class ResourceQuery(object):
    def __init__(self):
        # Map StorageResourceRecord ID to instantiated BaseStorageResource
        self._pk_to_resource = {}

        # Record plugins which fail to load
        self._errored_plugins = set()

    def record_all_ancestors(self, record):
        """Find an ancestor of type parent_klass, search depth first"""
        if not isinstance(record, StorageResourceRecord):
            record = StorageResourceRecord.objects.get(pk=record)

        result = [record]
        for p in record.parents.all():
            result.extend(self.record_all_ancestors(p))
        return result

    def record_all_alerts(self, record_id):
        if isinstance(record_id, StorageResourceRecord):
            record_id = record_id.pk

        from chroma_core.models import StorageResourceAlert, StorageAlertPropagated

        alerts = set(StorageResourceAlert.filter_by_item_id(StorageResourceRecord, record_id))
        for sap in StorageAlertPropagated.objects.filter(storage_resource=record_id):
            alerts.add(sap.alert_state)

        return alerts

    def resource_get_alerts(self, resource):
        # NB assumes resource is a out-of-plugin instance
        # which has _handle set to a DB PK
        assert resource._handle is not None
        from chroma_core.models import StorageResourceAlert

        resource_alerts = StorageResourceAlert.filter_by_item_id(StorageResourceRecord, resource._handle)

        return list(resource_alerts)

    def resource_get_propagated_alerts(self, resource):
        # NB assumes resource is a out-of-plugin instance
        # which has _handle set to a DB PK
        from chroma_core.models import StorageAlertPropagated

        alerts = []
        for sap in StorageAlertPropagated.objects.filter(storage_resource=resource._handle):
            alerts.append(sap.alert_state)
        return alerts

    def record_alert_message(self, record_id, alert_class):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        # Get the StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk=record_id)

        # Get the BaseStorageResource class and have it translate the alert_class
        klass = storage_plugin_manager.get_resource_class_by_id(record.resource_class_id)
        msg = "%s (%s %s)" % (klass.alert_message(alert_class), klass._meta.label, record.alias_or_name())
        return msg

    def record_class_and_instance_string(self, record):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        # Get the BaseStorageResource class and have it translate the alert_class
        klass = storage_plugin_manager.get_resource_class_by_id(record.resource_class_id)

        return klass._meta.label, record.to_resource().get_label()

    def _record_to_resource_parents(self, record):
        if isinstance(record, StorageResourceRecord):
            pk = record.pk
        else:
            pk = record

        if pk in self._pk_to_resource:
            storage_plugin_log.debug("Got record %s from cache" % record)
            return self._pk_to_resource[pk]
        else:
            resource = self._record_to_resource(record)
            if resource:
                resource._parents = [self._record_to_resource_parents(p) for p in record.parents.all()]
            return resource

    def _record_to_resource(self, record):
        """'record' may be a StorageResourceRecord or an ID.  Returns a
        BaseStorageResource, or None if the required plugin is unavailable"""
        # Conditional to allow passing in a record or an ID
        if not isinstance(record, StorageResourceRecord):
            if record in self._pk_to_resource:
                return self._pk_to_resource[record]
            record = StorageResourceRecord.objects.get(pk=record)
        else:
            if record.pk in self._pk_to_resource:
                return self._pk_to_resource[record.pk]

        plugin_module = record.resource_class.storage_plugin.module_name
        if plugin_module in [e for e in self._errored_plugins]:
            return None

        resource = record.to_resource()
        self._pk_to_resource[record.pk] = resource
        return resource

    # These get_ functions are wrapped in transactions to ensure that
    # e.g. after reading a parent relationship the parent record will really
    # still be there when we SELECT it.
    # XXX this could potentially cause problems if used from a view function
    # which depends on transaction behaviour, as we would commit their transaction
    # halfway through -- maybe use nested_commit_on_success?
    @transaction.atomic
    def get_resource(self, vrr):
        """Return a BaseStorageResource corresponding to a StorageResourceRecord
        identified by vrr_id.  May raise an exception if the plugin for that
        vrr cannot be loaded for any reason.

        Note: resource._parents will not be populated, you will only
        get the attributes."""

        return self._record_to_resource(vrr)

    @transaction.atomic
    def get_resource_parents(self, vrr_id):
        """Like get_resource by also fills out entire ancestry"""

        vrr = StorageResourceRecord.objects.get(pk=vrr_id)
        return self._record_to_resource_parents(vrr)

    @transaction.atomic
    def get_all_resources(self):
        """Return list of all resources for all plugins"""
        records = StorageResourceRecord.objects.all()

        resources = []
        for vrr in records:
            r = self._record_to_resource(vrr)
            if r:
                resources.append(r)
                for p in vrr.parents.all():
                    r._parents.append(self._record_to_resource(p))

        return resources

    def get_class_resources(self, class_or_classes, **kwargs):
        try:
            len(class_or_classes)
            classes = class_or_classes
        except TypeError:
            classes = [class_or_classes]

        records = StorageResourceRecord.objects.filter(resource_class__in=classes, **kwargs)
        return records

    def get_class_record_ids(self, resource_class):
        records = StorageResourceRecord.objects.filter(resource_class=resource_class).values("pk")
        for r in records:
            yield r["pk"]

    def _load_record_and_children(self, record):
        storage_plugin_log.debug("load_record_and_children: %s" % record)
        resource = self._record_to_resource_parents(record)
        if resource:
            children_records = StorageResourceRecord.objects.filter(parents=record)

            children_resources = []
            for c in children_records:
                child_resource = self._load_record_and_children(c)
                children_resources.append(child_resource)

            resource._children = children_resources
        return resource

    def get_resource_tree(self, root_records):
        """For a given plugin and resource class, find all instances of that class
        and return a tree of resource instances (with additional 'children' attribute)"""
        storage_plugin_log.debug(">> get_resource_tree")
        tree = []
        for record in root_records:
            tree.append(self._load_record_and_children(record))
        storage_plugin_log.debug("<< get_resource_tree")

        return tree

    def _record_by_attributes(self, fn, plugin, klass, **attrs):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        import json

        klass, klass_id = storage_plugin_manager.get_plugin_resource_class(plugin, klass)
        # FIXME: validate that attrs.keys() are all part of the resource's GlobalId
        resource = klass(**attrs)
        return fn(resource_class__id=klass_id, storage_id_str=json.dumps(resource.id_tuple()), storage_id_scope=None)

    def get_record_by_attributes(self, plugin, klass, **attrs):
        from chroma_core.models import StorageResourceRecord

        return self._record_by_attributes(StorageResourceRecord.objects.get, plugin, klass, **attrs)

    def filter_record_by_attributes(self, plugin, klass, **attrs):
        from chroma_core.models import StorageResourceRecord

        return self._record_by_attributes(StorageResourceRecord.objects.filter, plugin, klass, **attrs)

    def get_scannable_id_record_by_attributes(self, scope, plugin, klass, **attrs):
        # FIXME: horrendous function name indicating overcomplication
        # this is for getting a resource which uses a ScopedId identifier attribute
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        from chroma_core.models import StorageResourceRecord
        import json

        klass, klass_id = storage_plugin_manager.get_plugin_resource_class(plugin, klass)
        resource = klass(**attrs)
        return StorageResourceRecord.objects.get(
            resource_class__id=klass_id, storage_id_str=json.dumps(resource.id_tuple()), storage_id_scope=scope
        )
