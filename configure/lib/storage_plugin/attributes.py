

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


