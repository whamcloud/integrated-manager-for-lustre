

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines BaseResourceAttribute and its subclasses, which represent
the datatypes that StorageResource objects may store as attributes"""

from configure.lib.storage_plugin.base_resource_attribute import BaseResourceAttribute


class String(BaseResourceAttribute):
    def __init__(self, max_length = None, *args, **kwargs):
        self.max_length = max_length
        super(String, self).__init__(*args, **kwargs)

    def validate(self, value):
        if self.max_length != None and len(value) > self.max_length:
            raise ValueError("Value '%s' too long (max %s)" % (value, self.max_length))


class Boolean(BaseResourceAttribute):
    def encode(self, value):
        # Use an explicit 'encode' so that if someone sets the attribute to something
        # truthy but big (like a string) we don't end up storing that
        return bool(value)

    def decode(self, value):
        return value


class Integer(BaseResourceAttribute):
    def __init__(self, min_val = None, max_val = None, *args, **kwargs):
        self.min_val = min_val
        self.max_val = max_val
        super(Integer, self).__init__(*args, **kwargs)

    def validate(self, value):
        if self.min_val != None and value < self.min_val:
            raise ValueError("Value %s too low (min %s)" % (value, self.min_val))
        if self.max_val != None and value > self.max_val:
            raise ValueError("Value %s too high (max %s)" % (value, self.max_val))


# TODO: This is useful if the caller can give you an exact number of bytes
# , but where the caller has a "10GB" or somesuch, that's rounded
# and we should have an explicitly inexact Bytes class which would take
# a string and parse it to a rounded number of bytes.
class Bytes(BaseResourceAttribute):
    def to_markup(self, value):
        from monitor.lib.util import sizeof_fmt
        return sizeof_fmt(int(value))


class Enum(BaseResourceAttribute):
    def __init__(self, *args, **kwargs):
        self.options = args

        if not self.options:
            raise ValueError("Enum BaseResourceAttribute must be given 'options' argument")

        super(Enum, self).__init__(**kwargs)

    def validate(self, value):
        if not value in self.options:
            raise ValueError("Value '%s' is not one of %s" % (value, self.options))


class Uuid(BaseResourceAttribute):
    def validate(self, value):
        stripped = value.replace("-", "")
        if not len(stripped) == 32:
            raise ValueError("'%s' is not a valid UUID" % value)


class PosixPath(BaseResourceAttribute):
    pass


class HostName(BaseResourceAttribute):
    pass


class ResourceReference(BaseResourceAttribute):
    # NB no 'encode' impl here because it has to be a special case to
    # resolve a local resource to a global ID

    def decode(self, value):
        import json
        pk = json.loads(value)
        if pk:
            from configure.models import StorageResourceRecord

            record = StorageResourceRecord.objects.get(pk = pk)
            return record.to_resource()
        else:
            return None

    def to_markup(self, value):
        from configure.models import StorageResourceRecord
        if value == None:
            return ""

        record = StorageResourceRecord.objects.get(pk = value._handle)
        if record.alias:
            name = record.alias
        else:
            name = value.human_string()

        from django.utils.html import conditional_escape
        name = conditional_escape(name)

        from django.utils.safestring import mark_safe
        return mark_safe("<a class='storage_resource' href='#%s'>%s</a>" % (value._handle, name))

    def validate(self, value):
        from configure.lib.storage_plugin.resource import StorageResource
        if value == None and self.optional:
            return
        elif value == None and not self.optional:
            raise ValueError("ResourceReference set to None but not optional")
        elif not isinstance(value, StorageResource):
            raise ValueError("Cannot take ResourceReference to %s" % value)
