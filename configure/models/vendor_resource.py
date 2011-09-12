
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.db import models

class VendorResourceRecord(models.Model):
    vendor_plugin = models.CharField(max_length = 256)
    vendor_class_str = models.TextField()
    vendor_id_str = models.TextField()
    vendor_id_scope = models.ForeignKey('VendorResourceRecord', blank = True, null = True)
    parents = models.ManyToManyField('VendorResourceRecord', related_name = 'resource_parent')
    vendor_dict_str = models.TextField()

    class Meta:
        app_label = 'configure'

class VendorResourceAttribute(models.Model):
    key = models.CharField(max_length = 64)
    value = models.TextField()

