#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_core.models.storage_plugin import StorageResourceAttributeSerialized


class BaseResourceAttribute(object):
    """Base class for declared attributes of BaseStorageResource.  This is
    to BaseStorageResource as models.fields.Field is to models.Model

    """

    # This is a hack to store the order in which attributes are declared so
    # that I can sort the BaseStorageResource attribute dict for presentation in the same order
    # as the plugin author declared the attributes.
    creation_counter = 0

    model_class = StorageResourceAttributeSerialized

    def __init__(self,
                 optional = False,
                 label = None,
                 hidden = False,
                 user_read_only = False):
        """
        :param optional: If this is True, the attribute may be left unassigned (i.e. null).  Otherwise,
            a non-null value must be provided for all instances.
        :param label: Human readable string for use in the user interface.  Use this if the programmatic
            attribute name in the resource declaration is not appropriate for presentation to the user.
        :param hidden: If this is True, this attribute will not be included as a column in the tabular view
            of storage resources.
        :param user_read_only: If this is True, this attribute can only be set internally by the plugin, not
            by the user.  For example, a controller might have some attributes entered by the user, and some
            read from the hardware: those read from the hardware would be marked `user_read_only`.  Attributes
            which are `user_read_only` must also be `optional`.
        """
        self.optional = optional
        self.label = label
        self.hidden = hidden
        self.user_read_only = user_read_only

        self.creation_counter = BaseResourceAttribute.creation_counter
        BaseResourceAttribute.creation_counter += 1

    def get_label(self, name):
        if self.label:
            return self.label
        else:
            words = name.split("_")
            return " ".join([words[0].title()] + words[1:])

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
        return value

    def decode(self, value):
        return value

    def to_markup(self, value):
        from django.utils.html import conditional_escape
        return conditional_escape(value)
