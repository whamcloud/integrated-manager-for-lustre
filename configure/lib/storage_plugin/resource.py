
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This modules defines the VendorResource class, which VendorPlugins subclass use
to define their system elements"""

from configure.lib.storage_plugin.attributes import ResourceAttribute
from configure.lib.storage_plugin.statistics import ResourceStatistic
from configure.lib.storage_plugin.log import vendor_plugin_log
from configure.models import VendorResourceRecord

class VendorResourceMetaclass(type):
    def __new__(cls, name, bases, dct):
        dct['_vendor_attributes'] = {}
        dct['_vendor_statistics'] = {}

        for base in bases:
            if hasattr(base, '_vendor_attributes'):
                dct['_vendor_attributes'].update(base._vendor_attributes)
            if hasattr(base, '_vendor_statistics'):
                dct['_vendor_statistics'].update(base._vendor_statistics)

        #print "* %s" % name
        for field_name, field_obj in dct.items():
            from configure.lib.storage_plugin.attributes import PosixPath
        #    print "** %s %s %s %s" % (field_name, field_obj, isinstance(field_obj, ResourceAttribute), isinstance(field_obj, PosixPath))
            
            if isinstance(field_obj, ResourceAttribute):
                dct['_vendor_attributes'][field_name] = field_obj
                del dct[field_name]
            elif isinstance(field_obj, ResourceStatistic):
                dct['_vendor_attributes'][field_name] = field_obj
                del dct[field_name]

        #print "%s._vendor_attributes = %s" % (name, dct['_vendor_attributes'])

        return super(VendorResourceMetaclass, cls).__new__(cls, name, bases, dct)

class VendorResource(object):
    __metaclass__ = VendorResourceMetaclass

    icon = 'default'

    def __init__(self, **kwargs):
        self._vendor_dict = {}
        self._handle = None
        self._parents = []
        self._dirty_attributes = set()
        self._parents_dirty = False

        for k,v in kwargs.items():
            if not k in self._vendor_attributes:
                raise KeyError("Unknown attribute %s (not one of %s)" % (k, self._vendor_attributes.keys()))
            setattr(self, k, v)

    def to_json(self, stack = []):
        dct = {}
        dct['id'] = self._handle
        dct['human_string'] = self.human_string(stack)
        dct['human_class'] = self.human_class()
        dct['icon'] = self.icon
        dct.update(self.get_attributes_display())
        dct['children'] = []
        
        stack = stack + [self]
        # This is a bit ropey, .children is actually only added when doing a resource_tree from resourcemanager
        for c in self._children:
            dct['children'].append(c.to_json(stack))

        return dct

    def __str__(self):
        return "<%s %s>" % (self.__class__.__name__, self._handle)

    def human_string(self, ancestors=[]):
        """Subclasses should implement a function which formats a string for
        presentation, possibly in a tree display as a child of 'parent' (a 
        VendorResource instance) or if parent is None then for display 
        on its own."""
        return self.__str__()

    def __setattr__(self, key, value):
        if key.startswith("_") or not key in self._vendor_attributes:
            object.__setattr__(self, key, value)
        else:
            # First see if the new val is the same as an existing
            # value if there is an existing value, and if so return.
            try:
                old_val = self._vendor_dict[key]
                if old_val == value:
                    return
            except KeyError:
                pass

            # Value is new or changed, set it and mark dirty
            self._vendor_dict[key] = value
            self._dirty_attributes.add(key)

    def __getattr__(self, key):
        if key.startswith("_") or not key in self._vendor_attributes:
            raise AttributeError
        else:
            return self._vendor_dict[key]

    def dirty(self):
        return (len(self._dirty_attributes) > 0) or self._parents_dirty

    def save(self):
        if not self._handle:
            raise RuntimeError("Cannot save unregistered resource")
        if not self.dirty():
            return

        record = VendorResourceRecord.objects.get(pk = self._handle)

        for attr in self._dirty_attributes:
            record.update_attributes(self._vendor_dict)
            if self._vendor_dict.has_key(attr):
                record.update_attribute(attr, self._vendor_dict[attr])
            else:
                record.delete_attribute(attr)

        self._dirty_attributes.clear()

        if self._parents_dirty:
            existing_parents = record.parents.all()

            new_parent_handles = [r._handle for r in self._parents]
            for ep in existing_parents:
                if not ep.pk in new_parent_handles:
                    record.parents.remove(ep)
                    # TODO: discover if this now means the parent is an orphan

            existing_parent_handles = [ep.pk for ep in existing_parents]
            for p in self._parents:
                if not p._handle in existing_parent_handles:
                    record.parents.add(VendorResourceRecord.objects.get(pk = p._handle))
            

        record.save()

    @classmethod
    def attrs_to_id_str(cls, attrs):
        """Serialized ID for use in VendorResourceRecord.vendor_id_str"""
        import json
        identifier_val = []
        for f in cls.identifier.id_fields:
            identifier_val.append(attrs[f])
        return json.dumps(identifier_val)

    def id_str(self):
        """Serialized ID for use in VendorResourceRecord.vendor_id_str"""
        import json
        identifier_val = []
        for f in self.identifier.id_fields:
            identifier_val.append(getattr(self, f))
        return json.dumps(identifier_val)
    
    def get_attributes_display(self):
        """Return a list of 2-tuples for names and human readable
           values for all resource attributes (i.e. _vendor_dict)"""
        attributes = {}
        for k,v in self._vendor_dict.items():
            try:
                attribute_obj = self._vendor_attributes[k]
            except KeyError:
                # For non-declared fields, fall back to generic field
                attribute_obj = ResourceAttribute()
            
            attributes[k] = attribute_obj.human_readable(v) 
        return attributes

    def add_parent(self, parent_resource):
        if not parent_resource in self._parents:
            self._parents.append(parent_resource)
            self._parents_dirty = True

    def validate(self):
        """Call validate() on the ResourceAttribute for all _vendor_dict items, and
           ensure that all non-optional ResourceAttributes have a value in _vendor_dict"""
        for k,v in self._vendor_dict.items():
            if k in self._vendor_attributes:
                self._vendor_attributes[k].validate(v)

        for k,a in self._vendor_attributes.items():
            if not k in self._vendor_dict and not a.optional:
                raise ValueError("Missing mandatory attribute %s" % k)
                
    def get_parent(self, parent_klass):
        """Return one member of self._parents of class 'parent_klass'.  Raises 
           an exception if there are multiple matches or no matches."""
        parents_filtered = [p for p in self._parents if isinstance(p, parent_klass)]
        if len(parents_filtered) == 0:
            print self._parents
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
    def human_class(cls):
        if hasattr(cls, 'human_name'):
            return cls.human_name
        else:
            return cls.__name__

class LocalId(object):
    """An Id which is unique within the ancestor resource of type parent_klass"""
    def __init__(self, parent_klass, *args):
        args = list(args)
        assert(len(args) > 0)
        self.id_fields = args
        self.parent_klass = parent_klass

class GlobalId(object):
    """An Id which is globally unique"""
    def __init__(self, *args):
        args = list(args)
        assert(len(args) > 0)
        self.id_fields = args

