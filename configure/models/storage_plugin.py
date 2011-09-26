
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
import json


# Our limit on the length of python names where we put
# them in CharFields -- python doesn't impose a limit, so this
# is pretty arbitrary
MAX_NAME_LENGTH = 128

class StoragePluginRecord(models.Model):
    """Reference to a module defining a StoragePlugin subclass"""
    module_name = models.CharField(max_length = MAX_NAME_LENGTH)

    class Meta:
        unique_together = ('module_name',)
        app_label = 'configure'

class StorageResourceClass(models.Model):
    """Reference to a StorageResource subclass"""
    storage_plugin = models.ForeignKey(StoragePluginRecord)
    class_name = models.CharField(max_length = MAX_NAME_LENGTH)

    def __str__(self):
        return "%s/%s" % (self.storage_plugin.module_name, self.class_name)

    class Meta:
        unique_together = ('storage_plugin', 'class_name')
        app_label = 'configure'

class StorageResourceRecord(models.Model):
    """Reference to an instance of a StorageResource"""
    resource_class = models.ForeignKey(StorageResourceClass)

    # Representing a configure.lib.storage_plugin.GlobalId or LocalId
    storage_id_str = models.TextField()
    storage_id_scope = models.ForeignKey('StorageResourceRecord',
            blank = True, null = True)

    # Parent-child relationships between resources
    parents = models.ManyToManyField('StorageResourceRecord',
            related_name = 'resource_parent')

    def __str__(self):
        return "%s (record %s)" % (self.resource_class.class_name, self.pk)

    @classmethod
    def create_root(cls, resource_class, attrs):
        from configure.lib.storage_plugin import storage_plugin_manager
        # Root resource do not have parents so they must be globally identified
        from configure.lib.storage_plugin import GlobalId
        if not isinstance(resource_class.identifier, GlobalId):
            raise RuntimeError("Cannot create root resource of class %s, it is not globally identified" % resource_class_name)

        id_str = resource_class.attrs_to_id_str(attrs)
        plugin_mod = resource_class.__module__
        class_name = resource_class.__name__
        resource_class_id = storage_plugin_manager.get_plugin_resource_class_id(plugin_mod, class_name)

        # See if you're trying to create something which already exists
        try:
            existing_record = StorageResourceRecord.objects.get(
                    resource_class = resource_class_id,
                    storage_id_str = id_str,
                    storage_id_scope = None)
            raise RuntimeError("Cannot create root resource %s %s %s, a resource with the same global identifier already exists" % (plugin_mod, resource_class.__name__, attrs))
        except StorageResourceRecord.DoesNotExist:
            # Great, nothing in the way
            pass
        record = StorageResourceRecord(
                resource_class_id = resource_class_id,
                storage_id_str = id_str)
        record.save()
        for name, value in attrs.items():
            StorageResourceAttribute.objects.create(resource = record,
                    key = name, value = json.dumps(value))

        return record

    def update_attributes(self, storage_dict):
        # TODO: remove existing attrs not in storage_dict
        existing_attrs = [i['key'] for i in StorageResourceAttribute.objects.filter(resource = self).values('key')]

        for key, value in storage_dict.items():
            try:
                existing = StorageResourceAttribute.objects.get(resource = self, key = key)
                encoded_val = json.dumps(value)
                if existing.value != encoded_val:
                    existing.value = encoded_val
                    existing.save()
            except StorageResourceAttribute.DoesNotExist:
                attr = StorageResourceAttribute(resource = self, key = key, value = json.dumps(value))
                attr.save()

    def update_attribute(self, key, val):
        # Try to update an existing record
        updated = StorageResourceAttribute.objects.filter(
                    resource = self,
                    key = key).update(value = json.dumps(val))
        # If there was no existing record, create one
        if updated == 0:
            StorageResourceAttribute.objects.create(
                    resource = self,
                    key = key,
                    value = json.dumps(value))

    def delete_attribute(self, attr_name):
        try:
            StorageResourceAttribute.objects.get(
                    resource = self,
                    key = attr_name).delete()
        except StorageResourceAttribute.DoesNotExist:
            pass

    def items(self):
        for i in self.storageresourceattribute_set.all():
            yield (i.key, i.value)

    def to_resource(self):
        from configure.lib.storage_plugin import storage_plugin_manager
        klass = storage_plugin_manager.get_plugin_resource_class(
                self.resource_class.storage_plugin.module_name,
                self.resource_class.class_name)
        storage_dict = {}
        for attr in self.storageresourceattribute_set.all():
            storage_dict[attr.key] = json.loads(attr.value)
        resource = klass(**storage_dict)
        resource._handle = self.id
        return resource

    class Meta:
        # Can't have this constraint because storage_id_str is a blob
        #unique_together = ('resource_class', 'storage_id_str', 'storage_id_scope')
        app_label = 'configure'

class StorageResourceAttribute(models.Model):
    """An attribute of a StorageResource instance.
    
    Note that we store the denormalized key name of the attribute
    for each storageresource instance, to support schemaless attribute
    dictionaries.  If we made the executive decision to remove this
    and only allow explicitly declared fields, then we would normalize 
    out the attribute names.
    """
    resource = models.ForeignKey(StorageResourceRecord)
    # TODO: specialized attribute tables for common types like 
    # short strings, integers
    value = models.TextField()
    key = models.CharField(max_length = 64)

    class Meta:
        unique_together = ('resource', 'key')
        app_label = 'configure'

class StorageResourceClassStatistic(models.Model):
    resource_class = models.ForeignKey(StorageResourceClass)
    name = models.CharField(max_length = 64)

    class Meta:
        unique_together = ('resource_class', 'name')
        app_label = 'configure'

class StorageResourceStatistic(models.Model):
    resource = models.ForeignKey(StorageResourceRecord)
    resource_class_statistic = models.ForeignKey(StorageResourceClassStatistic)

    timestamp = models.DateTimeField()
    value = models.IntegerField()

    class Meta:
        app_label = 'configure'

from monitor.models import AlertState
class StorageResourceAlert(AlertState):
    """Used by configure.lib.storage_plugin"""

    # Within the plugin referenced by the alert_item, what kind
    # of alert is this?
    alert_class = models.CharField(max_length = 512)
    attribute = models.CharField(max_length = 128, blank = True, null = True)

    def __str__(self):
        return "<%s:%s %d>" % (self.alert_class, self.attribute, self.pk)
    def message(self):
        # TODO: map alert_class back to a message via the plugin
        alert_message = self.alert_class
        if self.attribute:
            return "%s on attribute '%s'" % (self.alert_class, self.attribute)
        else:
            return "%s" % self.alert_class

    class Meta:
        app_label = 'configure'


