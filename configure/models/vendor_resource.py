
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
import json


# Our limit on the length of python names where we put
# them in CharFields -- python doesn't impose a limit, so this
# is pretty arbitrary
MAX_NAME_LENGTH = 128

class VendorPluginRecord(models.Model):
    """Reference to a module defining a VendorPlugin subclass"""
    module_name = models.CharField(max_length = MAX_NAME_LENGTH)

    class Meta:
        unique_together = ('module_name',)
        app_label = 'configure'

class VendorResourceClass(models.Model):
    """Reference to a VendorResource subclass"""
    vendor_plugin = models.ForeignKey(VendorPluginRecord)
    class_name = models.CharField(max_length = MAX_NAME_LENGTH)

    def __str__(self):
        return "%s/%s" % (self.vendor_plugin.module_name, self.class_name)

    class Meta:
        unique_together = ('vendor_plugin', 'class_name')
        app_label = 'configure'

class VendorResourceRecord(models.Model):
    """Reference to an instance of a VendorResource"""
    resource_class = models.ForeignKey(VendorResourceClass)

    # Representing a configure.lib.storage_plugin.GlobalId or LocalId
    vendor_id_str = models.TextField()
    vendor_id_scope = models.ForeignKey('VendorResourceRecord',
            blank = True, null = True)

    # Parent-child relationships between resources
    parents = models.ManyToManyField('VendorResourceRecord',
            related_name = 'resource_parent')

    def __str__(self):
        return "%s (record %s)" % (self.resource_class.class_name, self.pk)

    @classmethod
    def create_root(cls, resource_class, attrs):
        from configure.lib.storage_plugin import vendor_plugin_manager
        # Root resource do not have parents so they must be globally identified
        from configure.lib.storage_plugin import GlobalId
        if not isinstance(resource_class.identifier, GlobalId):
            raise RuntimeError("Cannot create root resource of class %s, it is not globally identified" % resource_class_name)

        id_str = resource_class.attrs_to_id_str(attrs)
        plugin_mod = resource_class.__module__
        class_name = resource_class.__name__
        resource_class_id = vendor_plugin_manager.get_plugin_resource_class_id(plugin_mod, class_name)

        # See if you're trying to create something which already exists
        try:
            existing_record = VendorResourceRecord.objects.get(
                    resource_class = resource_class_id,
                    vendor_id_str = id_str,
                    vendor_id_scope = None)
            raise RuntimeError("Cannot create root resource %s %s %s, a resource with the same global identifier already exists" % (plugin_mod, resource_class.__name__, attrs))
        except VendorResourceRecord.DoesNotExist:
            # Great, nothing in the way
            pass
        record = VendorResourceRecord(
                resource_class_id = resource_class_id,
                vendor_id_str = id_str)
        record.save()
        for name, value in attrs.items():
            VendorResourceAttribute.objects.create(resource = record,
                    key = name, value = json.dumps(value))

        return record

    def update_attributes(self, vendor_dict):
        # TODO: remove existing attrs not in vendor_dict
        existing_attrs = [i['key'] for i in VendorResourceAttribute.objects.filter(resource = self).values('key')]

        for key, value in vendor_dict.items():
            try:
                existing = VendorResourceAttribute.objects.get(resource = self, key = key)
                encoded_val = json.dumps(value)
                if existing.value != encoded_val:
                    existing.value = encoded_val
                    existing.save()
            except VendorResourceAttribute.DoesNotExist:
                attr = VendorResourceAttribute(resource = self, key = key, value = json.dumps(value))
                attr.save()

    def update_attribute(self, key, val):
        # Try to update an existing record
        updated = VendorResourceAttribute.objects.filter(
                    resource = self,
                    key = key).update(value = json.dumps(val))
        # If there was no existing record, create one
        if updated == 0:
            VendorResourceAttribute.objects.create(
                    resource = self,
                    key = key,
                    value = json.dumps(value))

    def delete_attribute(self, attr_name):
        try:
            VendorResourceAttribute.objects.get(
                    resource = self,
                    key = attr_name).delete()
        except VendorResourceAttribute.DoesNotExist:
            pass

    def items(self):
        for i in self.vendorresourceattribute_set.all():
            yield (i.key, i.value)

    def to_resource(self):
        from configure.lib.storage_plugin import vendor_plugin_manager
        klass = vendor_plugin_manager.get_plugin_resource_class(
                self.resource_class.vendor_plugin.module_name,
                self.resource_class.class_name)
        vendor_dict = {}
        for attr in self.vendorresourceattribute_set.all():
            vendor_dict[attr.key] = json.loads(attr.value)
        resource = klass(**vendor_dict)
        resource._handle = self.id
        return resource

    class Meta:
        # Can't have this constraint because vendor_id_str is a blob
        #unique_together = ('resource_class', 'vendor_id_str', 'vendor_id_scope')
        app_label = 'configure'

class VendorResourceAttribute(models.Model):
    """An attribute of a VendorResource instance.
    
    Note that we store the denormalized key name of the attribute
    for each vendorresource instance, to support schemaless attribute
    dictionaries.  If we made the executive decision to remove this
    and only allow explicitly declared fields, then we would normalize 
    out the attribute names.
    """
    resource = models.ForeignKey(VendorResourceRecord)
    # TODO: specialized attribute tables for common types like 
    # short strings, integers
    value = models.TextField()
    key = models.CharField(max_length = 64)

    class Meta:
        unique_together = ('resource', 'key')
        app_label = 'configure'

class VendorResourceClassStatistic(models.Model):
    resource_class = models.ForeignKey(VendorResourceClass)
    name = models.CharField(max_length = 64)

    class Meta:
        unique_together = ('resource_class', 'name')
        app_label = 'configure'

class VendorResourceStatistic(models.Model):
    resource = models.ForeignKey(VendorResourceRecord)
    resource_class_statistic = models.ForeignKey(VendorResourceClassStatistic)

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


