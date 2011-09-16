

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines VendorPluginManager which loads and provides
access to VendorPlugins and their VendorResources"""

from configure.lib.storage_plugin.resource import VendorResource, GlobalId, LocalId
from configure.lib.storage_plugin.plugin import VendorPlugin
from configure.lib.storage_plugin.log import vendor_plugin_log
from configure.models import *
from django.db import transaction

class LoadedPlugin(object):
    """Convenience store of introspected information about loaded 
       plugin modules."""
    def __init__(self, module, plugin_class):
        # Map of name string to class
        self.resource_classes = {}
        self.module = module
        self.plugin_class = plugin_class
        self.plugin_record, created = VendorPluginRecord.objects.get_or_create(module_name = module.__name__)

        import inspect
        for name, cls in inspect.getmembers(module):
            if inspect.isclass(cls) and issubclass(cls, VendorResource) and cls != VendorResource:
                # FIXME: this limits plugin authors to putting everything in the same
                # module, don't forget to tell them that!  Doesn't mean they can't break
                # code up between files, but names must all be in the module.
                self.resource_classes[name] = cls
                vrc, created = VendorResourceClass.objects.get_or_create(
                        vendor_plugin = self.plugin_record,
                        class_name = name)

                # TODO: wrap this up somehow neater than just decorating the class
                # with an extra attribute
                cls.vendor_resource_class_id = vrc.id

                for name, stat_obj in cls._vendor_statistics.items():
                    class_stat, created = VendorResourceClassStatistic.objects.get_or_create(
                            resource_class = vrc,
                            name = name)

class ResourceQuery(object):
    def __init__(self):
        # Map VendorResourceRecord ID to instantiated VendorResource
        self._pk_to_resource = {}
        
        # Record plugins which fail to load
        self._errored_plugins = set()
        
    def _record_to_resource_parents(self, record):
        if record.pk in self._pk_to_resource:
            return self._pk_to_resource[record.pk]
        else:
            resource = self._record_to_resource(record)
            resource._parents = [self._record_to_resource_parents(p) for p in record.parents.all()]
            return resource

    def _record_to_resource(self, record):
        """'record' may be a VendorResourceRecord or an ID.  Returns a
        VendorResource, or None if the required plugin is unavailable"""
        
        if not isinstance(record, VendorResourceRecord):
            if record in self._pk_to_resource:
                return self._pk_to_resource[record]
            record = VendorResourceRecord.objects.get(pk=record)
        else:
            if record.pk in self._pk_to_resource:
                return self._pk_to_resource[record.pk]
            
        plugin_module = record.resource_class.vendor_plugin.module_name
        if plugin_module in self._errored_plugins:
            return None
            
        # We have to make sure the plugin is loaded before we
        # try to unpickle the VendorResource class
        try:
            vendor_plugin_manager.load_plugin(plugin_module)
        except:
            vendor_plugin_log.error("Cannot load plugin %s for VendorResourceRecord %d" % (plugin_module, record.id))
            self._errored_plugins.add(plugin_module)

        klass = vendor_plugin_manager.get_plugin_resource_class(
                record.resource_class.vendor_plugin.module_name,
                record.resource_class.class_name)
        assert(issubclass(klass, VendorResource))
        vendor_dict = {}
        for attr in record.vendorresourceattribute_set.all():
            vendor_dict[attr.key] = attr.value
        resource = klass(**vendor_dict)
        resource._handle = record.id

        return resource

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
        get the attributes."""

        vrr = VendorResourceRecord.objects.get(pk = vrr_id)
        return self._record_to_resource(vrr)

    @transaction.commit_on_success()
    def get_all_resources(self):
        """Return list of all resources for all plugins"""
        records = VendorResourceRecord.objects.all()

        resources = []
        resource_parents = {}
        for vrr in records:
            r = self._record_to_resource(vrr)
            if r:
                resources.append(r)
                for p in vrr.parents.all():
                    r._parents.append(self._record_to_resource(p))

        return resources

    def _load_record_and_children(self, record):
        resource = self._record_to_resource_parents(record)
        children_records = VendorResourceRecord.objects.filter(
            parents = record)
            
        children_resources = []
        for c in children_records:
            child_resource = self._load_record_and_children(c)
            children_resources.append(child_resource)

        resource._children = children_resources
        return resource

    def get_resource_tree(self, plugin_module, root_klass):
        """For a given plugin and resource class, find all instances of that class
        and return a tree of resource instances (with additional 'children' attribute)"""
        records = VendorResourceRecord.objects.filter(
            resource_class__class_name = root_klass,
            resource_class__vendor_plugin__module_name = plugin_module)
            
        tree = []
        for record in records:
            tree.append(self._load_record_and_children(record))
        
        return tree    

class VendorPluginManager(object):
    def __init__(self):
        self.loaded_plugins = {}
        self.plugin_sessions = {}

    def create_root_resource(self, plugin_mod, resource_class_name, **kwargs):
        vendor_plugin_log.debug("create_root_resource %s %s %s" % (plugin_mod, resource_class_name, kwargs))
        plugin_class = self.load_plugin(plugin_mod)

        # Try to find the resource class in the plugin module
        resource_class = self.get_plugin_resource_class(plugin_mod, resource_class_name)
        assert(issubclass(resource_class, VendorResource))

        # Root resource do not have parents so they must be globally identified
        assert(isinstance(resource_class.identifier, GlobalId))
        resource = resource_class(**kwargs)

        # See if you're trying to create something which already exists
        try:
            existing_record = VendorResourceRecord.objects.get(
                    resource_class__vendor_plugin__module_name = plugin_mod,
                    vendor_id_str = resource.id_str(),
                    vendor_id_scope = None)
            raise RuntimeError("Cannot create root resource %s %s %s, a resource with the same global identifier already exists" % (plugin_mod, resource_class_name, kwargs))
        except VendorResourceRecord.DoesNotExist:
            # Great, nothing in the way
            pass
        # XXX should we let people modify root records?  e.g. change the IP
        # address of a controller rather than deleting it, creating a new 
        # one and letting the pplugin repopulate us with 'new' resources?
        # This will present the challenge of what to do with instances of
        # VendorResource subclasses which are already present in running plugins.
        record = VendorResourceRecord(
                resource_class_id = resource_class.vendor_resource_class_id,
                vendor_id_str = resource.id_str())
        record.save()
        for name, value in kwargs.items():
            VendorResourceAttribute.objects.create(resource = record,
                    key = name, value = value)
            
        vendor_plugin_log.debug("create_root_resource created %d" % (record.id))

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



