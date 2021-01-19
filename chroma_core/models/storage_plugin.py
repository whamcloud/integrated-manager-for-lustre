# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

from collections import defaultdict
import json
import logging

from django.db import models
from django.db.models import CASCADE

from chroma_core.models import AlertEvent
from chroma_core.models import AlertStateBase
from chroma_core.models.host import Volume
from chroma_core.lib.storage_plugin.log import storage_plugin_log as log
from chroma_core.models.sparse_model import VariantDescriptor


# Our limit on the length of python names where we put
# them in CharFields -- python doesn't impose a limit, so this
# is pretty arbitrary
MAX_NAME_LENGTH = 128


class StoragePluginRecord(models.Model):
    """Reference to a module defining a BaseStoragePlugin subclass"""

    module_name = models.CharField(max_length=MAX_NAME_LENGTH)
    internal = models.BooleanField(default=False)

    class Meta:
        unique_together = ("module_name",)
        app_label = "chroma_core"
        ordering = ["id"]


class StorageResourceClass(models.Model):
    """Reference to a BaseStorageResource subclass"""

    storage_plugin = models.ForeignKey(StoragePluginRecord, on_delete=models.PROTECT)
    class_name = models.CharField(max_length=MAX_NAME_LENGTH)
    user_creatable = models.BooleanField(default=False)

    def __str__(self):
        return "%s/%s" % (self.storage_plugin.module_name, self.class_name)

    def get_class(self):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        return storage_plugin_manager.get_resource_class_by_id(self.pk)

    class Meta:
        unique_together = ("storage_plugin", "class_name")
        app_label = "chroma_core"
        ordering = ["id"]


class StorageResourceRecord(models.Model):
    """Reference to an instance of a BaseStorageResource"""

    resource_class = models.ForeignKey(StorageResourceClass, on_delete=models.PROTECT)

    # Representing a chroma_core.lib.storage_plugin.GlobalId or LocalId
    # TODO: put some checking for id_strs longer than this field: they
    # are considered 'unreasonable' and plugin authors should be
    # conservative in what they use for an ID
    storage_id_str = models.CharField(max_length=256)
    storage_id_scope = models.ForeignKey("StorageResourceRecord", blank=True, null=True, on_delete=models.PROTECT)

    # FIXME: when the id_scope is nullable a unique_together across it
    # doesn't enforce uniqueness for GlobalID resources

    # Parent-child relationships between resources
    parents = models.ManyToManyField("StorageResourceRecord", related_name="resource_parent")

    alias = models.CharField(max_length=64, blank=True, null=True)

    reported_by = models.ManyToManyField("StorageResourceRecord", related_name="resource_reported_by")

    class Meta:
        app_label = "chroma_core"
        unique_together = ("storage_id_str", "storage_id_scope", "resource_class")
        ordering = ["id"]

    def __str__(self):
        return self.alias_or_name()

    @classmethod
    def get_or_create_root(cls, resource_class, resource_class_id, attrs):
        # Root resource do not have parents so they must be globally identified
        from chroma_core.lib.storage_plugin.api.identifiers import AutoId, ScopedId

        if isinstance(resource_class._meta.identifier, ScopedId):
            raise RuntimeError("Cannot create root resource of class %s, it requires a scope" % resource_class)

        if isinstance(resource_class._meta.identifier, AutoId):
            import uuid

            attrs["chroma_auto_id"] = uuid.uuid4().__str__()
        id_str = json.dumps(resource_class.attrs_to_id_tuple(attrs, False))

        # NB assumes that none of the items in ID tuple are ResourceReferences: this
        # would raise an exception from json encoding.
        # FIXME: weird separate code path for creating resources (cf resourcemanager)
        try:
            # See if you're trying to create something which already exists
            existing_record = StorageResourceRecord.objects.get(
                resource_class=resource_class_id, storage_id_str=id_str, storage_id_scope=None
            )
            return existing_record, False
        except StorageResourceRecord.DoesNotExist:
            # Great, nothing in the way
            pass

        record = StorageResourceRecord(resource_class_id=resource_class_id, storage_id_str=id_str)
        record.save()

        log.info("StorageResourceRecord created %d" % (record.id))

        for name, value in attrs.items():
            attr_model_class = resource_class.attr_model_class(name)
            attr_model_class.objects.create(resource=record, key=name, value=attr_model_class.encode(value))

        return record, True

    def update_attributes(self, attributes):
        for key, val in attributes.items():
            self.update_attribute(key, val)

    def update_attribute(self, key, val):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        resource_class = storage_plugin_manager.get_resource_class_by_id(self.resource_class_id)

        # Try to update an existing record
        attr_model_class = resource_class.attr_model_class(key)
        updated = attr_model_class.objects.filter(resource=self, key=key).update(value=attr_model_class.encode(val))
        # If there was no existing record, create one
        if updated == 0:
            from django.db import IntegrityError

            try:
                attr_model_class.objects.create(resource=self, key=key, value=attr_model_class.encode(val))
            except IntegrityError:
                # Collided with another update, order undefined so let him win
                pass

    def delete_attribute(self, attr_name):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        resource_class = storage_plugin_manager.get_resource_class_by_id(self.resource_class_id)
        model_class = resource_class.attr_model_class(attr_name)
        try:
            model_class.objects.get(resource=self, key=attr_name).delete()
        except model_class.DoesNotExist:
            pass

    def items(self):
        for i in self.storageresourceattribute_set.all():
            yield (i.key, i.value)

    def to_resource(self):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        klass = storage_plugin_manager.get_resource_class_by_id(self.resource_class_id)
        attr_model_to_keys = defaultdict(list)
        for attr, attr_props in klass._meta.storage_attributes.items():
            attr_model_to_keys[attr_props.model_class].append(attr)
        storage_dict = {}
        for attr_model, keys in attr_model_to_keys.items():
            for attr in attr_model.objects.filter(resource=self, key__in=keys):
                storage_dict[attr.key] = attr_model.decode(attr.value)

        resource = klass(**storage_dict)
        resource._handle = self.id
        resource._handle_global = True
        return resource

    def alias_or_name(self, resource=None):
        if self.alias:
            return self.alias
        else:
            if not resource:
                resource = self.to_resource()
            return resource.get_label()

    def to_resource_class(self):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        klass, klass_id = storage_plugin_manager.get_plugin_resource_class(
            self.resource_class.storage_plugin.module_name, self.resource_class.class_name
        )
        return klass


class StorageResourceAttribute(models.Model):
    """An attribute of a BaseStorageResource instance.

    Note that we store the denormalized key name of the attribute
    for each storageresource instance, to support schemaless attribute
    dictionaries.  If we made the executive decision to remove this
    and only allow explicitly declared fields, then we would normalize
    out the attribute names.
    """

    @classmethod
    def encode(cls, value):
        return value

    @classmethod
    def decode(cls, value):
        return value

    resource = models.ForeignKey(StorageResourceRecord, on_delete=CASCADE)
    # TODO: normalize this field (store a list of attributes
    # with StorageResourceClass, that list would also be useful
    # for comparing against at plugin load time to e.g. complain
    # about new fields and/or mung existing records
    key = models.CharField(max_length=64)

    class Meta:
        abstract = True
        unique_together = ("resource", "key")
        app_label = "chroma_core"


class StorageResourceAttributeSerialized(StorageResourceAttribute):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    value = models.TextField()

    @classmethod
    def encode(cls, value):
        return json.dumps(value)

    @classmethod
    def decode(cls, value):
        return json.loads(value)


class StorageResourceAttributeReference(StorageResourceAttribute):
    class Meta:
        app_label = "chroma_core"
        ordering = ["id"]

    value = models.ForeignKey(
        StorageResourceRecord, blank=True, null=True, related_name="value_resource", on_delete=models.PROTECT
    )

    # NB no 'encode' impl here because it has to be a special case to
    # resolve a local resource to a global ID

    def __setattr__(self, k, v):
        if k == "value" and isinstance(v, int):
            return super(StorageResourceAttributeReference, self).__setattr__("value_id", v)
        else:
            return super(StorageResourceAttributeReference, self).__setattr__(k, v)

    @classmethod
    def decode(cls, value):
        if value:
            return value.to_resource()
        else:
            return None


class StorageResourceOffline(AlertStateBase):
    # Inability to contact a storage controller
    # does not directly impact the availability of
    # a filesystem, but it might hide issues which reduce it's performance,
    # such as a RAID rebuild.  Be pessimistic, say WARNING.
    default_severity = logging.WARNING

    class Meta:
        app_label = "chroma_core"
        proxy = True

    def alert_message(self):
        return "%s not contactable" % self.alert_item.alias_or_name()

    def end_event(self):
        return AlertEvent(
            message_str="Re-established contact with %s" % self.alert_item.alias_or_name(),
            alert_item=self.alert_item,
            alert=self,
            severity=logging.INFO,
        )


class StorageResourceAlert(AlertStateBase):
    """Used by chroma_core.lib.storage_plugin"""

    class Meta:
        app_label = "chroma_core"
        proxy = True

    variant_fields = [
        VariantDescriptor("alert_class", str, None, None, ""),
        VariantDescriptor("attribute", str, None, None, None),
    ]

    def __str__(self):
        return "<%s:%s %s>" % (self.alert_class, self.attribute, self.pk)

    def alert_message(self):
        from chroma_core.lib.storage_plugin.query import ResourceQuery

        msg = ResourceQuery().record_alert_message(self.alert_item.pk, self.alert_class)
        return msg

    def end_event(self):
        return AlertEvent(
            message_str="Cleared storage alert: %s" % self.message(),
            alert_item=self.alert_item,
            alert=self,
            severity=logging.INFO,
        )

    def affected_targets(self, affect_target):
        from chroma_core.models.target import get_host_targets

        affected_srrs = [
            sap["storage_resource_id"]
            for sap in StorageAlertPropagated.objects.filter(alert_state=self).values("storage_resource_id")
        ]
        affected_srrs.append(self.alert_item_id)
        luns = Volume.objects.filter(storage_resource__in=affected_srrs)
        for l in luns:
            for ln in l.volumenode_set.all():
                ts = get_host_targets(ln.host_id)
                for t in ts:
                    affect_target(t)


class StorageAlertPropagated(models.Model):
    storage_resource = models.ForeignKey(StorageResourceRecord, on_delete=CASCADE)
    alert_state = models.ForeignKey(StorageResourceAlert, on_delete=CASCADE)

    class Meta:
        unique_together = ("storage_resource", "alert_state")
        app_label = "chroma_core"
        ordering = ["id"]


class StorageResourceLearnEvent(AlertStateBase):
    variant_fields = [
        VariantDescriptor(
            "storage_resource",
            StorageResourceRecord,
            lambda self_: StorageResourceRecord.objects.get(id=self_.get_variant("storage_resource_id", None, int)),
            lambda self_, value: self_.set_variant("storage_resource_id", int, value.id),
            None,
        )
    ]

    @staticmethod
    def type_name():
        return "Storage resource detection"

    def alert_message(self):
        from chroma_core.lib.storage_plugin.query import ResourceQuery

        class_name, instance_name = ResourceQuery().record_class_and_instance_string(self.storage_resource)
        return "Discovered %s '%s'" % (class_name, instance_name)

    class Meta:
        app_label = "chroma_core"
        proxy = True
