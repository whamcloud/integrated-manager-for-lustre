
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This modules defines the StorageResource class, which StoragePlugins subclass use
to define their system elements"""

from chroma_core.lib.storage_plugin.base_resource_attribute import BaseResourceAttribute
from chroma_core.lib.storage_plugin.statistics import BaseStatistic
from chroma_core.lib.storage_plugin.alert_conditions import AlertCondition

from collections import defaultdict
import threading


class Statistic(object):
    def __init__(self):
        pass


class StorageResourceMetaclass(type):
    def __new__(cls, name, bases, dct):
        # Maps of attribute name to object
        dct['_storage_attributes'] = {}
        dct['_storage_statistics'] = {}
        dct['_alert_conditions'] = {}
        dct['_alert_classes'] = {}

        # Lists of attribute names
        dct['_provides'] = []
        dct['_subscribes'] = []

        for base in bases:
            if hasattr(base, '_storage_attributes'):
                dct['_storage_attributes'].update(base._storage_attributes)
            if hasattr(base, '_storage_statistics'):
                dct['_storage_statistics'].update(base._storage_statistics)
            if hasattr(base, '_alert_conditions'):
                dct['_alert_conditions'].update(base._alert_conditions)

        for field_name, field_obj in dct.items():
            if isinstance(field_obj, BaseResourceAttribute):
                dct['_storage_attributes'][field_name] = field_obj
                del dct[field_name]
                if field_obj.provide:
                    dct['_provides'].append((field_name, field_obj.provide))
                if field_obj.subscribe:
                    dct['_subscribes'].append((field_name, field_obj.subscribe))
            elif isinstance(field_obj, BaseStatistic):
                dct['_storage_statistics'][field_name] = field_obj
                del dct[field_name]
            elif isinstance(field_obj, AlertCondition):
                dct['_alert_conditions'][field_name] = field_obj
                field_obj.set_name(field_name)

                # Build map to find the AlertCondition which
                # generated a particular alert
                for alert_class in field_obj.alert_classes():
                    dct['_alert_classes'][alert_class] = field_obj

                del dct[field_name]

        return super(StorageResourceMetaclass, cls).__new__(cls, name, bases, dct)


class StorageResource(object):
    __metaclass__ = StorageResourceMetaclass

    icon = 'default'

    @classmethod
    def alert_message(cls, alert_class):
        return cls._alert_classes[alert_class].message

    @classmethod
    def encode(cls, attr, value):
        return cls._storage_attributes[attr].encode(value)

    @classmethod
    def decode(cls, attr, value):
        return cls._storage_attributes[attr].decode(value)

    def format(self, attr, val = None):
        if not val:
            val = getattr(self, attr)
        return self._storage_attributes[attr].to_markup(val)

    def format_all(self):
        """Return a list of 2-tuples for names and human readable
           values for all resource attributes (i.e. _storage_dict)"""
        for k in self._storage_dict.keys():
            yield k, self.format(k)

    def get_attribute_items(self):
        result = {}
        attr_props = self.get_all_attribute_properties()
        for name, props in attr_props:
            val = getattr(self, name)
            if isinstance(val, StorageResource):
                raw = val._handle
            else:
                raw = val
            result[name] = {'raw': raw, 'markup': props.to_markup(val), 'label': props.get_label(name)}
        return result

    @classmethod
    def get_all_attribute_properties(cls):
        attr_name_pairs = cls._storage_attributes.items()
        attr_name_pairs.sort(lambda a, b: cmp(a[1].creation_counter, b[1].creation_counter))
        return attr_name_pairs

    @classmethod
    def get_charts(cls):
        if hasattr(cls, 'charts'):
            return cls.charts
        else:
            charts = []
            for name, stat_props in cls._storage_statistics.items():
                if stat_props.label:
                    label = stat_props.label
                else:
                    label = name

                charts.append({
                    'title': label,
                    'series': [name]
                    })

            return charts

    @classmethod
    def get_attribute_properties(cls, name):
        return cls._storage_attributes[name]

    def __init__(self, **kwargs):
        self._storage_dict = {}
        self._handle = None
        self._handle_global = None
        if 'parents' in kwargs:
            self._parents = list(kwargs['parents'])
            del kwargs['parents']
        else:
            self._parents = []

        # Accumulate changes since last call to flush_deltas()
        self._delta_lock = threading.Lock()
        self._delta_attrs = {}
        self._delta_parents = []

        # Accumulate in between calls to flush_stats()
        self._delta_stats_lock = threading.Lock()
        self._delta_stats = defaultdict(list)

        for k, v in kwargs.items():
            if not k in self._storage_attributes:
                raise KeyError("Unknown attribute %s (not one of %s)" % (k, self._storage_attributes.keys()))
            setattr(self, k, v)
        self.flush_deltas()

    def flush_deltas(self):
        with self._delta_lock:
            deltas = {'attributes': self._delta_attrs,
                      'parents': self._delta_parents}
            self._delta_attrs = {}
            self._delta_parents = []

        # Blackhawk down!
        return deltas

    @classmethod
    def get_columns(cls):
        return [{'name': name, 'label': props.get_label(name)} for (name, props) in cls._storage_attributes.items()]

    def to_json(self, stack = []):
        dct = {}
        dct['id'] = self._handle
        dct['label'] = self.get_label()
        dct['class_label'] = self.get_class_label()
        dct['icon'] = self.icon
        dct.update(dict(list(self.format_all())))
        dct['children'] = []

        stack = stack + [self]
        # This is a bit ropey, .children is actually only added when doing a resource_tree from resourcemanager
        for c in self._children:
            dct['children'].append(c.to_json(stack))

        return dct

    def __str__(self):
        return "<%s %s>" % (self.__class__.__name__, self._handle)

    def get_label(self, ancestors=[]):
        """Subclasses should implement a function which formats a string for
        presentation, possibly in a tree display as a child of 'parent' (a
        StorageResource instance) or if parent is None then for display
        on its own."""
        id = self.id_tuple()
        if len(id) == 1:
            id = id[0]
        return "%s %s" % (self.get_class_label(), id)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            # Do this check first to avoid extra dict lookups for access
            # to internal vars
            object.__setattr__(self, key, value)
        elif key in self._storage_attributes:
            # Validate the value
            self._storage_attributes[key].validate(value)

            # First see if the new val is the same as an existing
            # value if there is an existing value, and if so return.
            try:
                old_val = self._storage_dict[key]
                if old_val == value:
                    return
            except KeyError:
                pass

            self._storage_dict[key] = value
            with self._delta_lock:
                self._delta_attrs[key] = value
        elif key in self._storage_statistics:
            stat_obj = self._storage_statistics[key]
            stat_obj.validate(value)

            import time
            with self._delta_stats_lock:
                self._delta_stats[key].append({
                            "timestamp": int(time.time()),
                            "value": value})
        else:
            object.__setattr__(self, key, value)

    def flush_stats(self):
        with self._delta_stats_lock:
            tmp = self._delta_stats
            self._delta_stats = defaultdict(list)
        return tmp

    def __getattr__(self, key):
        if key.startswith("_") or not key in self._storage_attributes:
            raise AttributeError("Unknown attribute %s" % key)
        else:
            try:
                return self._storage_dict[key]
            except KeyError:
                attr = self._storage_attributes[key]
                if attr.optional:
                    return None
                else:
                    raise AttributeError("attribute %s not found" % key)

    @classmethod
    def attrs_to_id_tuple(cls, attrs):
        """Serialized ID for use in StorageResourceRecord.storage_id_str"""
        identifier_val = []
        for f in cls.identifier.id_fields:
            if f in attrs:
                identifier_val.append(attrs[f])
            else:
                identifier_val.append(None)
        return tuple(identifier_val)

    def id_tuple(self):
        return self.attrs_to_id_tuple(self._storage_dict)

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
            if k in self._storage_attributes:
                self._storage_attributes[k].validate(v)

        for k, a in self._storage_attributes.items():
            if not k in self._storage_dict and not a.optional:
                raise ValueError("Missing mandatory attribute %s" % k)

    def get_parent(self, parent_klass):
        """Return one member of self._parents of class 'parent_klass'.  Raises
           an exception if there are multiple matches or no matches."""
        parents_filtered = [p for p in self._parents if isinstance(p, parent_klass)]
        if len(parents_filtered) == 0:
            raise RuntimeError("No parents of class %s" % parent_klass)
        elif len(parents_filtered) > 1:
            raise RuntimeError("Multiple parents of class %s" % parent_klass)
        else:
            return parents_filtered[0]

    def get_parents(self):
        """Template helper b/c templates aren't allowed to touch _members"""
        return self._parents

    def get_handle(self):
        """Template helper"""
        return self._handle

    @classmethod
    def get_class_label(cls):
        if hasattr(cls, 'class_label'):
            return cls.class_label
        else:
            return cls.__name__


class GlobalId(object):
    """An Id which is globally unique"""
    def __init__(self, *args):
        args = list(args)
        assert(len(args) > 0)
        self.id_fields = args


class ScannableId(GlobalId):
    """An Id which is unique within a scannable resource"""
    pass


class ScannableResource(object):
    """Used for marking which StorageResource subclasses are for scanning (like couplets, hosts)"""
    pass


class ScannableStorageResource(StorageResource, ScannableResource):
    pass
