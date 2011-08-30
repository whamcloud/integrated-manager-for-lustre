
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module provides functions to be used by storage hardware plugins
to hydra."""

import json
import pickle
import settings
from collections_24 import defaultdict
from django.db import transaction

from configure.models import VendorResourceRecord

# Configure logging
from logging import getLogger, DEBUG, WARNING, StreamHandler, FileHandler
vendor_plugin_log = getLogger('vendor_plugin_log')
vendor_plugin_log.addHandler(FileHandler('vendor_plugin.log'))
if settings.DEBUG:
    vendor_plugin_log.setLevel(DEBUG)
    vendor_plugin_log.addHandler(StreamHandler())
else:
    vendor_plugin_log.setLevel(WARNING)

class VendorPlugin(object):
    def __init__(self):
        self._handle = vendor_plugin_manager.register_plugin(self)
        # TODO: give each one its own log, or at least a prefix
        self.log = vendor_plugin_log

    def initial_scan(self):
        """To be implemented by subclasses.  Identify all resources
           present at this time and call add_resource on them.
           
           Any plugin which throws an exception from here is assumed
           to be broken - this will not be retried.  If one of your
           controllers is not contactable, you must handle that and 
           when it comes back up let us know during an update call."""
        raise NotImplementedError

    def get_root_resources(self):
        """Return any existing resources for this plugin which
           have no parents.  e.g. depending on the plugin this
           might be chassis, hosts.  Usually something that 
           holds an IP address for this plugin to reach out to.
           Plugins may call this during their initial_scan 
           implementation.

           This information is not simply included in the arguments
           to initial_scan, because some plugins may either use 
           their own autodiscovery mechanism or run locally on 
           a controller and therefore need no hints from us."""
        records = VendorResourceRecord.objects.\
               filter(vendor_plugin = self.__class__.__module__).\
               filter(parents = None)
        #from django.db.models import Count,F
        #records = VendorResourceRecord.objects.\
        #       filter(vendor_plugin = self.__class__.__module__).\
        #       annotate(Count('parents')).\
        #       filter(F('parents__count') = 0)

        resources = []
        for vrr in records:
            klass = vendor_plugin_manager.get_plugin_resource_class(vrr.vendor_plugin, vrr.vendor_class_str)
            assert(issubclass(klass, VendorResource))
            # Skip populating VendorResource._parents
            vendor_dict = json.loads(vrr.vendor_dict_str)
            resource = klass(**vendor_dict)
            resource._handle = vrr.id
            resources.append(resource)

        return resources

    def add_resource(self, resource):
        """Register a resource:
           * Validate its attributes
           * Create a VendorResourceRecord if it doesn't already
             exist.
           * Update VendorResourceRecord.vendor_dict from resource._vendor_dict
           * Populate its _handle attribute with a reference
             to a VendorResourceRecord.
             
           You may only call this once per plugin instance on 
           a particular resource."""
        assert(isinstance(resource, VendorResource))
        assert(self._handle)
        assert(not resource._handle)

        resource.validate()

        id_string = resource.id_str()

        if isinstance(resource.identifier, GlobalId):
            id_scope = None
        elif isinstance(resource.identifier, LocalId):
            # TODO: support ancestors rather than just parents
            scope_parent = None
            for p in resource._parents:
                if isinstance(p, resource.identifier.parent_klass):
                    scope_parent = p
            if not scope_parent:
                raise RuntimeError("Resource %s scoped to resource of type %s, but has no parent of that type!  Its parents are: %s" % (resource, resource.identifier.parent_klass, resource._parents))
            if not scope_parent._handle:
                raise RuntimeError("Resource %s's scope parent %s has not been registered yet (parents must be registered before children)" % (resource, scope_parent))

            id_scope = VendorResourceRecord.objects.get(pk=scope_parent._handle)

        record, created = VendorResourceRecord.objects.get_or_create(
                vendor_plugin = resource.__class__.__module__,
                vendor_class_str = resource.__class__.__name__,
                vendor_id_str = id_string,
                vendor_id_scope = id_scope)

        record.vendor_dict_str = json.dumps(resource._vendor_dict)
        record.save()

        resource._handle = record.pk
        if created:
            vendor_plugin_log.info("Created VendorResourceRecord for %s id=%s" % (resource.__class__.__name__, id_string))
        else:
            vendor_plugin_log.debug("Looked up VendorResourceRecord %s for %s id=%s" % (record.id, resource.__class__.__name__, id_string))

        for parent in resource._parents:
            if not parent._handle:
                raise RuntimeError("Parent resources must be registered before their children")
            parent_record = VendorResourceRecord.objects.get(pk = parent._handle)
            record.parents.add(parent_record)

class LoadedPlugin(object):
    """Convenience store of introspected information about loaded 
       plugin modules."""
    def __init__(self, module, plugin_class):
        # Map of name string to class
        self.resource_classes = {}
        self.module = module
        self.plugin_class = plugin_class

        import inspect
        for name, cls in inspect.getmembers(module):
            if inspect.isclass(cls) and issubclass(cls, VendorResource) and cls != VendorResource:
                self.resource_classes[name] = cls

class VendorPluginManager(object):
    def __init__(self):
        self.loaded_plugins = {}
        self.plugin_sessions = {}

    def create_root_resource(self, plugin_mod, resource_class_name, **kwargs):
        vendor_plugin_log.debug("create_root_resource %s %s %s" % (plugin_mod, resource_class_name, kwargs))
        plugin_class = self.load_plugin(plugin_mod)

        # Try to find the resource class in the plugin module
        # FIXME: this limits plugin authors to putting everything in the same
        # module, don't forget to tell them that!  Doesn't mean they can't break
        # code up between files, but names must all be in the module.
        resource_class = self.get_plugin_resource_class(plugin_mod, resource_class_name)
        assert(issubclass(resource_class, VendorResource))

        # Root resource do not have parents so they must be globally identified
        assert(isinstance(resource_class.identifier, GlobalId))
        resource = resource_class(**kwargs)

        # See if you're trying to create something which already exists
        try:
            existing_record = VendorResourceRecord.objects.get(vendor_plugin = plugin_mod, vendor_id_str = resource.id_str(), vendor_id_scope = None)
            raise RuntimeError("Cannot create root resource %s %s %s, a resource with the same global identifier already exists" % (plugin_mod, resource_class_name, kwargs))
        except VendorResourceRecord.DoesNotExist:
            # Great, nothing in the way
            pass
        # XXX should we let people modify root records?  e.g. change the IP
        # address of a controller rather than deleting it, creating a new 
        # one and letting the pplugin repopulate us with 'new' resources?
        record = VendorResourceRecord(
                vendor_plugin = plugin_mod,
                vendor_class_str = resource_class.__name__,
                vendor_id_str = resource.id_str(),
                vendor_dict_str = json.dumps(resource._vendor_dict))
        record.save()
        vendor_plugin_log.debug("create_root_resource created %d" % (record.id))

    # These get_ functions are wrapped in transactions to ensure that 
    # e.g. after reading a parent relationship the parent record will really
    # still be there when we SELECT it.
    # XXX this could potentially cause problems if used from a view function
    # which depends on transaction behaviour, as we would commit their transaction
    # halfway through -- maybe use nested_commit_on_success?
    @transaction.commit_on_success()
    def get_resource(self, vrr_id):
        """Return a VendorResource corresponding to a VendorResourceRecord
        identified by vrr_id.  May raise an exception if the plugin for that
        vrr cannot be loaded for any reason.

        Note: resource._parents will not be populated, you will only
        get the attributes.  If you want ancestors too, call get_resource_tree."""

        vrr = VendorResourceRecord.objects.get(pk = vrr_id)
        plugin_module = vrr.vendor_plugin
        # We have to make sure the plugin is loaded before we
        # try to unpickle the VendorResource class
        try:
            self.load_plugin(plugin_module)
        except:
            vendor_plugin_log.error("Cannot load plugin %s for VendorResourceRecord %d" % (plugin_module, vrr.id))
            errored_plugins.add(plugin_module)

        klass = self.get_plugin_resource_class(vrr.vendor_plugin, vrr.vendor_class_str)
        assert(issubclass(klass, VendorResource))
        vendor_dict = json.loads(vrr.vendor_dict_str)
        resource = klass(**vendor_dict)
        resource._handle = vrr.id

        return resource

    @transaction.commit_on_success()
    def get_resource_tree(self, vrr_id):
        """Like get_resource, but look up all a resource's ancestor's too"""
        # TODO: implement me.
        raise NotImplementedError()

    @transaction.commit_on_success()
    def get_all_resources(self):
        """Return list of all resources for all plugins"""
        records = VendorResourceRecord.objects.all()

        # Map VendorResourceRecord ID to instantiated VendorResource
        pk_to_resource = {}

        # Stash the list of parent IDs for each resource so that
        # we can populate the parents at the end when all resources
        # are loaded.
        resource_parents = defaultdict(list)

        errored_plugins = set()
        resources = []
        for vrr in records:
            plugin_module = vrr.vendor_plugin

            # Once we've realised a plugin isn't loadable, avoid
            # logging an error for every record that used it.
            if plugin_module in errored_plugins:
                continue

            # We have to make sure the plugin is loaded before we
            # try to unpickle the VendorResource class
            try:
                self.load_plugin(plugin_module)
            except:
                vendor_plugin_log.error("Cannot load plugin %s for VendorResourceRecord %d: further records using this plugin will be ignored" % (plugin_module, vrr.id))
                errored_plugins.add(plugin_module)

            klass = self.get_plugin_resource_class(vrr.vendor_plugin, vrr.vendor_class_str)
            assert(issubclass(klass, VendorResource))
            vendor_dict = json.loads(vrr.vendor_dict_str)
            resource = klass(**vendor_dict)
            resource._handle = vrr.id
            pk_to_resource[vrr.id] = resource

        # Finally loop over all loaded resources and populate ._parents
        for pk, resource in pk_to_resource.items():
            for parent_id in resource_parents[pk]:
                resource.add_parent(pk_to_resource[parent_id])

        return pk_to_resource.values()

    def register_plugin(self, plugin_instance):
        """Register a particular instance of a VendorPlugin"""
        # FIXME: only supporting one instance of a plugin class at a time
        session_id = plugin_instance.__class__.__name__
        assert(not session_id in self.plugin_sessions)

        self.plugin_sessions[session_id] = plugin_instance
        vendor_plugin_log.info("Registered plugin instance %s with id %s" % (plugin_instance, session_id))
        return session_id

    def get_plugin_resource_class(self, plugin_module, resource_class_name):
        loaded_plugin = self.loaded_plugins[plugin_module]
        return loaded_plugin.resource_classes[resource_class_name]

    def load_plugin(self, module):
        """Load a VendorPlugin class from a module given a
           python path like 'configure.lib.lvm',
           or simply return it if it was already loaded.  Note that the 
           VendorPlugin within the module will not be instantiated when this
           returns, caller is responsible for instantiating it.

           @return A subclass of VendorPlugin"""
        if module in self.loaded_plugins:
            return self.loaded_plugins[module].plugin_class

        # Load the module
        mod = __import__(module)
        components = module.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        plugin = mod

        # Find all VendorPlugin subclasses in the module
        plugin_klasses = []
        import inspect
        for name, cls in inspect.getmembers(plugin):
            if inspect.isclass(cls) and issubclass(cls, VendorPlugin) and cls != VendorPlugin:
                plugin_klasses.append(cls)
                
        # Make sure we have exactly one VendorPlugin subclass
        if len(plugin_klasses) > 1:
            raise RuntimeError("Module %s defines more than one VendorPlugin: %s!" % (module, plugin_klasses))
        elif len(plugin_klasses) == 0:
            raise RuntimeError("Module %s does not define a VendorPlugin!" % module)
        else:
            plugin_klass = plugin_klasses[0]

        self.loaded_plugins[plugin_klass.__module__] = LoadedPlugin(plugin, plugin_klass)
        return plugin_klass

vendor_plugin_manager = VendorPluginManager()

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

class VendorResource(object):
    def __init__(self, **kwargs):
        self._vendor_attributes = self._fields
        self._vendor_dict = {}
        self._handle = None
        self._parents = []

        for k,v in kwargs.items():
            if not k in self._vendor_attributes:
                raise KeyError("Unknown attribute %s (not one of %s)" % (k, self._vendor_attributes.keys()))
            setattr(self, k, v)

    def get_handle(self):
        return self._handle

    def __str__(self):
        return "<%s %s>" % (self.__class__.__name__, self._handle)

    def __setattr__(self, key, value):
        if key.startswith("_") or not key in self._vendor_attributes:
            object.__setattr__(self, key, value)
        else:
            self._vendor_dict[key] = value

    def __getattr__(self, key):
        if key.startswith("_") or not key in self._vendor_attributes:
            raise AttributeError
        else:
            return self._vendor_dict[key]

    def id_str(self):
        """Serialized ID for use in VendorResourceRecord.vendor_id_str"""
        identifier_val = []
        for f in self.identifier.id_fields:
            identifier_val.append(getattr(self, f))
        return json.dumps(identifier_val)
    
    def get_attributes_display(self):
        """Return a list of 2-tuples for names and human readable
           values for all resource attributes (i.e. _vendor_dict)"""
        attributes = []
        for k,v in self._vendor_dict.items():
            try:
                attribute_obj = self._vendor_attributes[k]
            except KeyError:
                # For non-declared fields, fall back to generic field
                attribute_obj = ResourceAttribute()
            attributes.append((k, attribute_obj.human_readable(v))) 
        return attributes

    def add_parent(self, parent_resource):
        self._parents.append(parent_resource)

    def validate(self):
        """Call validate() on the ResourceAttribute for all _vendor_dict items, and
           ensure that all non-optional ResourceAttributes have a value in _vendor_dict"""
        for k,v in self._vendor_dict.items():
            if k in self._vendor_attributes:
                self._vendor_attributes[k].validate(v)

        for k,a in self._vendor_attributes.items():
            if not k in self._vendor_dict and not a.optional:
                raise ValueError("Missing mandator attribute %s" % k)

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


