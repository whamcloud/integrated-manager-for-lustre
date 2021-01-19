# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""The following classes allow plugin authors to specify type and bound information
for the attributes of their resources.  Plugin authors are encouraged to be as specific
as possible in their choice of attribute class, and avoid using generic types like
String as much as possible.

"""
import re
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource

from chroma_core.lib.storage_plugin.base_resource_attribute import BaseResourceAttribute
from chroma_core.models.storage_plugin import StorageResourceAttributeReference


class String(BaseResourceAttribute):
    """A unicode string.  A maximum length may optionally be specified in the
    constructor using the ``max_length`` keyword argument"""

    def __init__(self, max_length=None, *args, **kwargs):
        assert (type(max_length) is int) or (max_length is None), (
            "max_length is not an integer or None: %s" % max_length
        )

        self.max_length = max_length
        super(String, self).__init__(*args, **kwargs)

    def validate(self, value):
        if (self.max_length is not None) and (len(value) > self.max_length):
            raise ValueError("Value '%s' too long (max %s)" % (value, self.max_length))


class Password(String):
    """A password.  Plugins must provide their own obfuscation function.
    The encryption function will be called by the manager server when processing user input (e.g.
    when a resource is added in the UI).  The obfuscated text will be seen by
    the plugin when the resource is retrieved.

    ::

        def encrypt_fn(password):
            return rot13(password)

        Password(encrypt_fn)"""

    def __init__(self, encrypt_fn, *args, **kwargs):
        assert hasattr(encrypt_fn, "__call__"), "encrypt_fn must be callable: %s" % encrypt_fn

        self.encrypt_fn = encrypt_fn
        super(Password, self).__init__(*args, **kwargs)

    def encrypt(self, value):
        return self.encrypt_fn(value)


class Boolean(BaseResourceAttribute):
    """A True/False value.  Any truthy value may be assigned to this, but it will be
    stored as True or False."""

    def cast(self, value):
        return bool(value)


class Integer(BaseResourceAttribute):
    """An integer.  This may optionally be bounded by setting the inclusive
    ``min_val`` and/or ``max_val`` keyword arguments to the constructor."""

    def __init__(self, min_val=None, max_val=None, *args, **kwargs):
        self.min_val = self.cast(min_val)
        self.max_val = self.cast(max_val)
        super(Integer, self).__init__(*args, **kwargs)

    def validate(self, value):
        value = self.cast(value)

        if (self.min_val is not None) and (value < self.min_val):
            raise ValueError("Value %s too low (min %s)" % (value, self.min_val))
        if (self.max_val is not None) and (value > self.max_val):
            raise ValueError("Value %s too high (max %s)" % (value, self.max_val))

    def cast(self, value):
        return None if value is None else int(value)


# TODO: This is useful if the caller can give you an exact number of bytes
# , but where the caller has a "10GB" or somesuch, that's rounded
# and we should have an explicitly inexact Bytes class which would take
# a string and parse it to a rounded number of bytes.
class Bytes(Integer):
    """An exact size in bytes.  This will be formatted with appropriate units
    and rounding when presented to the user, and should be used in preference to
    storing values in kilobytes/megabytes, etc., wherever possible."""

    def to_markup(self, value):
        from chroma_core.lib.util import sizeof_fmt

        return sizeof_fmt(int(value))


class Enum(BaseResourceAttribute):
    """An enumerated type.  Arguments to the constructor are the possible values, for example

    ::

      status = Enum('good', 'bad', 'ugly')
      ...
      status = 'good'  # valid
      status = 'other' # invalid

    Assigning any value not in those options will fail validation.  When presented to the user,
    this will appear as a dropdown box of available options."""

    def __init__(self, *args, **kwargs):
        self.options = args

        if not self.options:
            raise ValueError("Enum BaseResourceAttribute must be given 'options' argument")

        super(Enum, self).__init__(**kwargs)

    def validate(self, value):
        if not value in self.options:
            raise ValueError("Value '%s' is not one of %s" % (value, self.options))


class Uuid(BaseResourceAttribute):
    """A UUID string.  Arguments may have any style of hyphenation.  For example:

    ::

       wwn = Uuid()
       ...
       resource.wwn = "b44f7d8e-a40d-4b96-b241-2ab462b4c1c1"  # valid
       resource.wwn = "b44f7d8ea40d4b96b2412ab462b4c1c1"  # valid
       resource.wwn = "other"  # invalid
    """

    def validate(self, value):
        stripped = value.replace("-", "")
        if not len(stripped) == 32:
            raise ValueError("'%s' is not a valid UUID" % value)


class PosixPath(BaseResourceAttribute):
    """A POSIX filesystem path, e.g. /tmp/myfile.txt"""

    pass


class Hostname(BaseResourceAttribute):
    """A DNS hostname or an IP address, e.g. mycompany.com, 192.168.0.67"""

    pattern = re.compile("(?!-)[a-zA-Z\d-]{1,63}(?<!-)$")

    def validate(self, value):
        if len(value) > 255 or not all(map(self.pattern.match, value.split("."))):
            raise ValueError("'%s' is not a valid hostname" % value)


class ResourceReference(BaseResourceAttribute):
    """A reference to another resource.  Conceptually similar to a
    foreign key in a database.  Assign
    instantiated BaseStorageResource objects to this attribute.  When a storage
    resource is deleted, any other resources having a reference to it are affected:

    * If the ResourceReference has ``optional = True`` then the field is cleared
    * Otherwise, the referencing resource is also deleted

    .. note::

       Creating circular reference relationships using
       this attribute has undefined (most likely fatal) behaviour.

    """

    model_class = StorageResourceAttributeReference

    def to_markup(self, value):
        from chroma_core.models import StorageResourceRecord

        if value is None:
            return ""

        record = StorageResourceRecord.objects.get(pk=value._handle)
        if record.alias:
            name = record.alias
        else:
            name = value.get_label()

        from django.utils.html import conditional_escape

        name = conditional_escape(name)

        from django.utils.safestring import mark_safe

        return mark_safe("%s" % name)

    def validate(self, value):
        if value is None and self.optional:
            return
        elif (value is None) and (not self.optional):
            raise ValueError("ResourceReference set to None but not optional")
        elif not isinstance(value, BaseStorageResource):
            raise ValueError("Cannot take ResourceReference to %s" % value)
