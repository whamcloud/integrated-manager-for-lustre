

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines ResourceAttribute and its subclasses, which represent
the datatypes that StorageResource objects may store as attributes"""

class ResourceAttribute(object):
    """Base class for declared attributes of StorageResource.  This is
       to StorageResource as models.fields.Field is to models.Model"""
    def __init__(self, subscribe = False, provide = False, optional = False):
        self.optional = optional
        self.subscribe = subscribe
        self.provide = provide

    def validate(self, value):
        """Note: this validation is NOT intended to be used for catching cases 
        in production, it does not provide hooks for user-friendly error messages 
        etc.  Think of it more as an assert."""
        pass

    def human_readable(self, value):
        """Subclasses should format their value for human consumption, e.g.
           1024 => 1kB"""
        return value

    def encode(self, value):
        import json
        return json.dumps(value)

    def decode(self, value):
        import json
        return json.loads(value)

    def to_markup(self, value):
        from django.utils.html import conditional_escape
        return conditional_escape(value)

class String(ResourceAttribute):
    def __init__(self, max_length = None, *args, **kwargs):
        self.max_length = max_length
        super(String, self).__init__(*args, **kwargs)

    def validate(self, value):
        if self.max_length != None and len(value) > self.max_length:
            raise RuntimeError("Value '%s' too long (max %s)" % (value, self.max_length))

class Integer(ResourceAttribute):
    def __init__(self, min_val = None, max_val = None, *args, **kwargs):
        self.min_val = min_val
        self.max_val = max_val
        super(Integer, self).__init__(*args, **kwargs)

    def validate(self, value):
        if self.min_val != None and value < self.min_val:
            raise RuntimeError("Value %s too low (min %s)" % (value, self.min_val))
        if self.max_val != None and value > self.max_val:
            raise RuntimeError("Value %s too high (max %s)" % (value, self.max_val))

# TODO: This is useful if the caller can give you an exact number of bytes
# , but where the caller has a "10GB" or somesuch, that's rounded
# and we should have an explicitly inexact Bytes class which would take
# a string and parse it to a rounded number of bytes.

class Bytes(ResourceAttribute):
    def to_markup(self, value):
        from monitor.lib.util import sizeof_fmt
        return sizeof_fmt(int(value))

class Enum(ResourceAttribute):
    def __init__(self, *args, **kwargs):
        self.options = args

        if not self.options:
            raise ValueError("Enum ResourceAttribute must be given 'options' argument")

        super(Enum, self).__init__(**kwargs)

    def validate(self, value):
        if not value in self.options:
            raise ValueError("Value '%s' is not one of %s" % (value, self.options))

class Uuid(ResourceAttribute):
    def validate(self, value):
        stripped = value.replace("-", "")
        if not len(stripped) == 32:
            raise ValueError("'%s' is not a valid UUID" % value)

class PosixPath(ResourceAttribute):
    pass

class HostName(ResourceAttribute):
    pass

class ResourceReference(ResourceAttribute):
    # NB no 'encode' impl here because it has to be a special case to 
    # resolve a local resource to a global ID

    def decode(self, value):
        import json
        pk = json.loads(value)

        from configure.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk = pk)
        return record.to_resource()
        
    def to_markup(self, value):
        from django.core.urlresolvers import reverse
        url = reverse('configure.views.storage_resource', kwargs = {'srr_id': value._handle})

        from configure.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk = value._handle)
        if record.alias:
            name = record.alias
        else:
            name = value.human_string()

        from django.utils.html import conditional_escape
        name = conditional_escape(name)

        from django.utils.safestring import mark_safe
        return mark_safe("<a href='%s'>%s</a>" % (url, name))

    def validate(self, value):
        from configure.lib.storage_plugin.resource import StorageResource
        if not isinstance(value, StorageResource):
            raise RuntimeError("Cannot take ResourceReference to %s" % value)


