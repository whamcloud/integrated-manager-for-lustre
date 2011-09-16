
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models
from picklefield.fields import PickledObjectField

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

    def update_attributes(self, vendor_dict):
        import json

        existing_attrs = [i['key'] for i in VendorResourceAttribute.objects.filter(resource = self).values('key')]

        for key, value in vendor_dict.items():
            attr, created = VendorResourceAttribute.objects.get_or_create(
                    resource = self, key = key)
            attr.value = json.dumps(value)
            attr.save()

    def update_attribute(self, key, val):
        # Try to update an existing record
        updated = VendorResourceAttribute.objects.filter(
                    resource = self,
                    key = key).update(value = val)
        # If there was no existing record, create one
        if updated == 0:
            VendorResourceAttribute.objects.create(
                    resource = self,
                    key = key,
                    value = value)

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
    # TODO: use JSON instead of pickling for storing 'arbitrary'
    # values to improve readability when debugging the database
    # and avoid risk of python junk in the DB
    value = PickledObjectField()
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

