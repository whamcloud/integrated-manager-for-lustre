

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines StoragePluginManager which loads and provides
access to StoragePlugins and their StorageResources"""

from configure.lib.storage_plugin.resource import StorageResource, GlobalId, ScannableResource
from configure.lib.storage_plugin.plugin import StoragePlugin
from configure.lib.storage_plugin.log import storage_plugin_log
from configure.models import *
from django.db import transaction
import json

class LoadedResourceClass(object):
    """Convenience store of introspected information about StorageResource 
       subclasses from loaded modules."""
    def __init__(self, resource_class, resource_class_id):
        self.resource_class = resource_class
        self.resource_class_id = resource_class_id

class LoadedPlugin(object):
    """Convenience store of introspected information about loaded 
       plugin modules."""
    def __init__(self, module, plugin_class):
        # Map of name string to class
        self.resource_classes = {}
        self.module = module
        self.plugin_class = plugin_class
        self.plugin_record, created = StoragePluginRecord.objects.get_or_create(module_name = module.__name__)
        self.scannable_resource_classes = []

        import inspect
        for name, cls in inspect.getmembers(module):
            if inspect.isclass(cls) and issubclass(cls, StorageResource) and cls != StorageResource:
                if issubclass(cls, ScannableResource):
                    self.scannable_resource_classes.append(name)

                # FIXME: this limits plugin authors to putting everything in the same
                # module, don't forget to tell them that!  Doesn't mean they can't break
                # code up between files, but names must all be in the module.
                vrc, created = StorageResourceClass.objects.get_or_create(
                        storage_plugin = self.plugin_record,
                        class_name = name)

                self.resource_classes[name] = LoadedResourceClass(cls, vrc.id)

                for name, stat_obj in cls._storage_statistics.items():
                    class_stat, created = StorageResourceClassStatistic.objects.get_or_create(
                            resource_class = vrc,
                            name = name)

class ResourceQuery(object):
    def __init__(self):
        # Map StorageResourceRecord ID to instantiated StorageResource
        self._pk_to_resource = {}
        
        # Record plugins which fail to load
        self._errored_plugins = set()

    def record_has_children(self, record_id):
        n = StorageResourceRecord.objects.filter(parents = record_id).count()
        return (n > 0)

    def record_find_parent(self, record, parent_klass):
        from configure.models import StorageResourceRecord

        if not isinstance(record, StorageResourceRecord):
            record = StorageResourceRecord.objects.get(pk=record)

        if issubclass(record.to_resource_class(), parent_klass):
            return record.pk

        for p in record.parents.all():
            found = self.record_find_parent(p, parent_klass)
            if found:
                return found

        return None

    def resource_get_alerts(self, resource):
        # NB assumes resource is a out-of-plugin instance
        # which has _handle set to a DB PK
        assert(resource._handle != None)
        from configure.models import StorageResourceAlert
        from configure.models import StorageResourceRecord
        resource_alerts = StorageResourceAlert.filter_by_item_id(
                StorageResourceRecord, resource._handle)

        return list(resource_alerts)

    def resource_get_propagated_alerts(self, resource):
        # NB assumes resource is a out-of-plugin instance
        # which has _handle set to a DB PK
        from configure.models import StorageAlertPropagated
        alerts = []
        for sap in StorageAlertPropagated.objects.filter(storage_resource = resource._handle):
            alerts.append(sap.alert_state)
        return alerts

    def record_alert_message(self, record_id, alert_class):
        # Get the StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk=record_id)

        # Load the appropriate plugin
        plugin_module = record.resource_class.storage_plugin.module_name

        # Get the StorageResource class and have it translate the alert_class
        klass = storage_plugin_manager.get_plugin_resource_class(
            record.resource_class.storage_plugin.module_name,
            record.resource_class.class_name)
        msg = klass.alert_message(alert_class)
        return msg

    def record_class_and_instance_string(self, record):
        # Load the appropriate plugin
        plugin_module = record.resource_class.storage_plugin.module_name

        # Get the StorageResource class and have it translate the alert_class
        klass = storage_plugin_manager.get_plugin_resource_class(
            record.resource_class.storage_plugin.module_name,
            record.resource_class.class_name)

        return klass.human_class(), record.to_resource().human_string()
        
    def _record_to_resource_parents(self, record):
        if isinstance(record, StorageResourceRecord):
            pk = record.pk
        else:
            pk = record

        if pk in self._pk_to_resource:
            storage_plugin_log.debug("Got record %s from cache" % record)
            return self._pk_to_resource[pk]
        else:
            resource = self._record_to_resource(record)
            if resource:
                resource._parents = [self._record_to_resource_parents(p) for p in record.parents.all()]
            return resource

    def _record_to_resource(self, record):
        """'record' may be a StorageResourceRecord or an ID.  Returns a
        StorageResource, or None if the required plugin is unavailable"""
        
        # Conditional to allow passing in a record or an ID
        if not isinstance(record, StorageResourceRecord):
            if record in self._pk_to_resource:
                return self._pk_to_resource[record]
            record = StorageResourceRecord.objects.get(pk=record)
        else:
            if record.pk in self._pk_to_resource:
                return self._pk_to_resource[record.pk]
            
        plugin_module = record.resource_class.storage_plugin.module_name
        if plugin_module in self._errored_plugins:
            return None
            
        resource = record.to_resource()
        self._pk_to_resource[record.pk] = resource
        return resource

    # These get_ functions are wrapped in transactions to ensure that 
    # e.g. after reading a parent relationship the parent record will really
    # still be there when we SELECT it.
    # XXX this could potentially cause problems if used from a view function
    # which depends on transaction behaviour, as we would commit their transaction
    # halfway through -- maybe use nested_commit_on_success?
    @transaction.commit_on_success()
    def get_resource(self, vrr):
        """Return a StorageResource corresponding to a StorageResourceRecord
        identified by vrr_id.  May raise an exception if the plugin for that
        vrr cannot be loaded for any reason.

        Note: resource._parents will not be populated, you will only
        get the attributes."""

        return self._record_to_resource(vrr)

    @transaction.commit_on_success()
    def get_resource_parents(self, vrr_id):
        """Like get_resource by also fills out entire ancestry"""

        vrr = StorageResourceRecord.objects.get(pk = vrr_id)
        return self._record_to_resource_parents(vrr)

    @transaction.commit_on_success()
    def get_all_resources(self):
        """Return list of all resources for all plugins"""
        records = StorageResourceRecord.objects.all()

        resources = []
        for vrr in records:
            r = self._record_to_resource(vrr)
            if r:
                resources.append(r)
                for p in vrr.parents.all():
                    r._parents.append(self._record_to_resource(p))

        return resources

    def get_class_resources(self, class_or_classes, **kwargs):
        try:
            n = len(class_or_classes)
            classes = class_or_classes
        except TypeError:
            classes = [class_or_classes]
            
        records = StorageResourceRecord.objects.filter(resource_class__in = classes, **kwargs)
        for r in records:
            res = self._record_to_resource(r)
            if res:
                yield res

    def get_class_record_ids(self, resource_class):
        records = StorageResourceRecord.objects.filter(
                resource_class = resource_class).values('pk')
        for r in records:
            yield r['pk']
    
    def _load_record_and_children(self, record):
        storage_plugin_log.debug("load_record_and_children: %s" % record)
        resource = self._record_to_resource_parents(record)
        if resource:
            children_records = StorageResourceRecord.objects.filter(
                parents = record)
                
            children_resources = []
            for c in children_records:
                child_resource = self._load_record_and_children(c)
                children_resources.append(child_resource)

            resource._children = children_resources
        return resource

    def get_resource_tree(self, root_records):
        """For a given plugin and resource class, find all instances of that class
        and return a tree of resource instances (with additional 'children' attribute)"""
        storage_plugin_log.debug(">> get_resource_tree")
        tree = []
        for record in root_records:
            tree.append(self._load_record_and_children(record))
        storage_plugin_log.debug("<< get_resource_tree")
        
        return tree    

class StoragePluginManager(object):
    def __init__(self):
        self.loaded_plugins = {}
        self.plugin_sessions = {}

        from settings import INSTALLED_STORAGE_PLUGINS
        for plugin in INSTALLED_STORAGE_PLUGINS:
            self.load_plugin(plugin)

    def get_scannable_resource_ids(self, plugin):
        loaded_plugin = self.loaded_plugins[plugin]
        return StorageResourceRecord.objects.\
               filter(resource_class__storage_plugin = loaded_plugin.plugin_record).\
               filter(resource_class__class_name__in = loaded_plugin.scannable_resource_classes).\
               filter(parents = None).values('id')

    @transaction.commit_on_success
    def create_root_resource(self, plugin_mod, resource_class_name, **kwargs):
        storage_plugin_log.debug("create_root_resource %s %s %s" % (plugin_mod, resource_class_name, kwargs))
        # Try to find the resource class in the plugin module
        resource_class = self.get_plugin_resource_class(plugin_mod, resource_class_name)

        # Construct a record
        record = StorageResourceRecord.create_root(resource_class, kwargs)

        # XXX should we let people modify root records?  e.g. change the IP
        # address of a controller rather than deleting it, creating a new 
        # one and letting the pplugin repopulate us with 'new' resources?
        # This will present the challenge of what to do with instances of
        # StorageResource subclasses which are already present in running plugins.

        storage_plugin_log.debug("create_root_resource created %d" % (record.id))

    def register_plugin(self, plugin_instance):
        """Register a particular instance of a StoragePlugin"""
        # FIXME: session ID not really used for anything, it's a vague
        # nod to the future remote-run plugins.
        session_id = plugin_instance.__class__.__name__

        self.plugin_sessions[session_id] = plugin_instance
        storage_plugin_log.info("Registered plugin instance %s with id %s" % (plugin_instance, session_id))
        return session_id

    def get_plugin_resource_class(self, plugin_module, resource_class_name):
        """Return a StorageResource subclass"""
        try:
            loaded_plugin = self.loaded_plugins[plugin_module]
        except KeyError:
            raise RuntimeError("Plugin %s not found (not one of %s)" % (plugin_module, self.loaded_plugins.keys()))
        return loaded_plugin.resource_classes[resource_class_name].resource_class

    def get_plugin_resource_class_id(self, plugin_module, resource_class_name):
        """Return a StorageResourceClass primary key"""
        loaded_plugin = self.loaded_plugins[plugin_module]
        return loaded_plugin.resource_classes[resource_class_name].resource_class_id

    def get_all_resources(self):
        for plugin in self.loaded_plugins.values():
            for loaded_res in plugin.resource_classes.values():
                yield (loaded_res.resource_class_id, loaded_res.resource_class)

    def get_plugin_class(self, module):
        return self.loaded_plugins[module].plugin_class

    def load_plugin(self, module):
        """Load a StoragePlugin class from a module given a
           python path like 'configure.lib.lvm',
           or simply return it if it was already loaded.  Note that the 
           StoragePlugin within the module will not be instantiated when this
           returns, caller is responsible for instantiating it.

           @return A subclass of StoragePlugin"""
        if module in self.loaded_plugins:
            return self.loaded_plugins[module].plugin_class

        # Load the module
        mod = __import__(module)
        components = module.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        plugin = mod

        # Find all StoragePlugin subclasses in the module
        plugin_klasses = []
        import inspect
        for name, cls in inspect.getmembers(plugin):
            if inspect.isclass(cls) and issubclass(cls, StoragePlugin) and cls != StoragePlugin:
                plugin_klasses.append(cls)
                
        # Make sure we have exactly one StoragePlugin subclass
        if len(plugin_klasses) > 1:
            raise RuntimeError("Module %s defines more than one StoragePlugin: %s!" % (module, plugin_klasses))
        elif len(plugin_klasses) == 0:
            raise RuntimeError("Module %s does not define a StoragePlugin!" % module)
        else:
            plugin_klass = plugin_klasses[0]

        self.loaded_plugins[plugin_klass.__module__] = LoadedPlugin(plugin, plugin_klass)
        return plugin_klass

storage_plugin_manager = StoragePluginManager()



