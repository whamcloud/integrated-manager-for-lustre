

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines ResourceAttribute and its subclasses, which represent
the datatypes that VendorResource objects may store as attributes"""

class ResourceAttribute(object):
    """Base class for declared attributes of VendorResource.  This is
       to VendorResource as models.fields.Field is to models.Model"""
    def __init__(self, optional = False):
        self.optional = optional

    def validate(self, value):
        """Note: this validation is NOT intended to be used for catching cases 
        in production, it does not provide hooks for user-friendly error messages 
        etc.  Think of it more as an assert."""
        pass

    def human_readable(self, value):
        """Subclasses should format their value for human consumption, e.g.
           1024 => 1kB"""
        return value

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
    def human_readable(self, value):
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




