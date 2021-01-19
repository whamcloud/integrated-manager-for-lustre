# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import time
from collections import defaultdict
from exceptions import KeyError, AttributeError, RuntimeError, ValueError
import threading
from chroma_core.lib.storage_plugin.base_resource_attribute import BaseResourceAttribute
from chroma_core.lib.storage_plugin.log import storage_plugin_log as log


class ResourceIdentifier(object):
    def __init__(self, *args):
        args = list(args)
        assert len(args) > 0
        self.id_fields = args


class BaseGlobalId(ResourceIdentifier):
    pass


class BaseAutoId(BaseGlobalId):
    def __init__(self):
        super(BaseAutoId, self).__init__("chroma_auto_id")


class BaseScopedId(ResourceIdentifier):
    pass


class ResourceProgrammingError(Exception):
    def __init__(self, class_name, message):
        self.message = message
        self.class_name = class_name

    def __str__(self):
        return "Resource class '%s': %s" % (self.class_name, self.message)


class StorageResourceMetaclass(type):
    def __new__(mcs, name, bases, dct):
        try:
            meta = dct["Meta"]
            del dct["Meta"]
        except KeyError:
            meta = type("Meta", (object,), {})

        if not hasattr(meta, "relations"):
            meta.relations = []
        if not hasattr(meta, "alert_conditions"):
            meta.alert_conditions = []
        if not hasattr(meta, "alert_classes"):
            meta.alert_classes = {}
        if not hasattr(meta, "storage_attributes"):
            meta.storage_attributes = {}
        if not hasattr(meta, "label"):
            meta.label = name

        meta.orig_relations = list(meta.relations)

        for base in bases:
            if name != "BaseStorageResource" and issubclass(base, BaseStorageResource):
                meta.storage_attributes.update(base._meta.storage_attributes)
                meta.alert_conditions.extend(base._meta.alert_conditions)
                meta.alert_classes.update(base._meta.alert_classes)
                meta.relations.extend(base._meta.relations)

        for field_name, field_obj in dct.items():
            if isinstance(field_obj, BaseResourceAttribute):
                meta.storage_attributes[field_name] = field_obj
                del dct[field_name]

        if hasattr(meta, "identifier") and isinstance(meta.identifier, BaseAutoId):
            from chroma_core.lib.storage_plugin.api.attributes import String

            field_obj = String(hidden=True)
            meta.storage_attributes["chroma_auto_id"] = field_obj

        # Build map to find the AlertCondition which
        # generated a particular alert
        all_alert_classes = set()
        for alert_condition in meta.alert_conditions:
            alert_classes = alert_condition.alert_classes()
            if set(alert_classes) & all_alert_classes:
                raise ResourceProgrammingError(
                    name, "Multiple AlertConditions on the same attribute must be disambiguated with 'id' parameters."
                )
            for alert_class in alert_classes:
                meta.alert_classes[alert_class] = alert_condition
            all_alert_classes |= set(alert_classes)

        dct["_meta"] = meta

        return super(StorageResourceMetaclass, mcs).__new__(mcs, name, bases, dct)


class BaseStorageResource(object):
    __metaclass__ = StorageResourceMetaclass

    icon = "default"

    def __init__(self, **kwargs):
        self._storage_dict = {}
        self._handle = None
        self._handle_global = None

        self._parents = list(kwargs.pop("parents", []))

        # Accumulate changes since last call to flush_deltas()
        self._delta_lock = threading.Lock()
        self._delta_attrs = {}
        self._delta_parents = []
        self._calc_changes_delta = kwargs.pop("calc_changes_delta", lambda: True)

        for k, v in kwargs.items():
            if not k in self._meta.storage_attributes:
                raise KeyError("Unknown attribute %s (not one of %s)" % (k, self._meta.storage_attributes.keys()))
            setattr(self, k, v)
        self.flush_deltas()

    @classmethod
    def alert_message(cls, alert_class):
        return cls._meta.alert_classes[alert_class].message

    @classmethod
    def encode(cls, attr, value):
        return cls._meta.storage_attributes[attr].encode(value)

    @classmethod
    def attr_model_class(cls, attr):
        return cls._meta.storage_attributes[attr].model_class

    @classmethod
    def decode(cls, attr, value):
        return cls._meta.storage_attributes[attr].decode(value)

    def format(self, attr, val=None):
        if not val:
            val = getattr(self, attr)
        return self._meta.storage_attributes[attr].to_markup(val)

    def format_all(self):
        """Return a list of 2-tuples for names and human readable
        values for all resource attributes (i.e. _storage_dict)"""
        for k in self._storage_dict.keys():
            yield k, self.format(k)

    @classmethod
    def get_all_attribute_properties(cls):
        """Returns a list of (name, BaseAttribute), one for each attribute.  Excludes hidden attributes."""
        attr_name_pairs = cls._meta.storage_attributes.items()
        attr_name_pairs.sort(lambda a, b: cmp(a[1].creation_counter, b[1].creation_counter))
        return [pair for pair in attr_name_pairs if not pair[1].hidden]

    @classmethod
    def get_attribute_properties(cls, name):
        return cls._meta.storage_attributes[name]

    def flush_deltas(self):
        with self._delta_lock:
            deltas = {"attributes": self._delta_attrs, "parents": self._delta_parents}
            self._delta_attrs = {}
            self._delta_parents = []

        return deltas

    def __str__(self):
        return "<%s %s>" % (self.__class__.__name__, self._handle)

    def get_label(self):
        """Subclasses should implement a function which formats a string for
        presentation, possibly in a tree display as a child of 'parent' (a
        BaseStorageResource instance) or if parent is None then for display
        on its own."""
        id = self.id_tuple()
        if len(id) == 1:
            id = id[0]
        return "%s %s" % (self._meta.label, id)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            # Do this check first to avoid extra dict lookups for access
            # to internal vars
            object.__setattr__(self, key, value)
        elif key in self._meta.storage_attributes:
            # Validate the value
            self._meta.storage_attributes[key].validate(value)

            # First see if the new val is the same as an existing
            # value if there is an existing value, and if so return.
            if self._calc_changes_delta():
                try:
                    old_val = self._storage_dict[key]
                    if old_val == value:
                        return
                except KeyError:
                    pass

            self._storage_dict[key] = value
            with self._delta_lock:
                self._delta_attrs[key] = value

        else:
            object.__setattr__(self, key, value)

    def __getattr__(self, key):
        if key.startswith("_") or not key in self._meta.storage_attributes:
            raise AttributeError("Unknown attribute %s" % key)
        else:
            try:
                return self._storage_dict[key]
            except KeyError:
                attr = self._meta.storage_attributes[key]
                if attr.optional:
                    return None
                elif attr.default is not None:
                    if callable(attr.default):
                        return attr.default(self._storage_dict)
                    else:
                        return attr.default
                else:
                    log.error("Missing attribute %s, %s" % (key, self._storage_dict))
                    raise AttributeError("attribute %s not found" % key)

    @classmethod
    def attrs_to_id_tuple(cls, attrs, null_missing):
        """Serialized ID for use in StorageResourceRecord.storage_id_str"""
        identifier_val = []
        for f in cls._meta.identifier.id_fields:
            if not f in cls._meta.storage_attributes:
                raise RuntimeError("Invalid attribute %s named in identifier for %s" % (f, cls))

            if f in attrs:
                identifier_val.append(attrs[f])
            else:
                if cls._meta.storage_attributes[f].optional or null_missing:
                    identifier_val.append(None)
                else:
                    raise RuntimeError("Missing ID attribute '%s'" % f)
        return tuple(identifier_val)

    def id_tuple(self):
        return self.attrs_to_id_tuple(self._storage_dict, False)

    @classmethod
    def compare_id_tuple(self, tuple1, tuple2, allow_missing):
        """
        Compare two id tuples and return True if they are the equal or False if they are different. If allow_missing is
        True then None values are not compared.
        :param tuple1:
        :param tuple2:
        :param allow_missing:
        :return: True if the tuples match.
        """
        if allow_missing:
            if len(tuple1) != len(tuple2):
                return False

            for value1, value2 in zip(tuple1, tuple2):
                if (value1 is not None) and (value2 is not None) and (value1 != value2):
                    return False

            return True
        else:
            return tuple1 == tuple2

    def add_parent(self, parent_resource):
        # TODO: lock _parents
        with self._delta_lock:
            if parent_resource not in self._parents:
                self._parents.append(parent_resource)
                self._delta_parents.append(parent_resource)

    def remove_parent(self, parent_resource):
        # TODO: lock _parents
        with self._delta_lock:
            if parent_resource in self._parents:
                self._parents.remove(parent_resource)
                self._delta_parents.append(parent_resource)

    def validate(self):
        """Call validate() on the BaseResourceAttribute for all _storage_dict items, and
        ensure that all non-optional BaseResourceAttributes have a value in _storage_dict"""
        for k, v in self._storage_dict.items():
            if k in self._meta.storage_attributes:
                self._meta.storage_attributes[k].validate(v)

        for k, a in self._meta.storage_attributes.items():
            if not k in self._storage_dict and not a.optional:
                raise ValueError("Missing mandatory attribute %s" % k)

    def get_parent(self, parent_klass):
        """Return one member of self._parents of class 'parent_klass'.  Raises
        an exception if there are multiple matches or no matches."""
        parents_filtered = [p for p in self._parents if isinstance(p, parent_klass)]
        if not parents_filtered:
            raise RuntimeError("No parents of class %s" % parent_klass)
        elif len(parents_filtered) > 1:
            raise RuntimeError("Multiple parents of class %s" % parent_klass)
        else:
            return parents_filtered[0]

    def get_parents(self):
        return self._parents

    @property
    def identifier_values(self):
        return tuple(getattr(self, id_field) for id_field in self._meta.identifier.id_fields)

    @property
    def identifier(self):
        return self._meta.identifier


class BaseScannableResource(object):
    """Used for marking which BaseStorageResource subclasses are for scanning (like couplets, hosts)"""

    pass


class HostsideResource(object):
    """Resources which are the agent-side equivalent of a BaseScannableResource"""

    pass
