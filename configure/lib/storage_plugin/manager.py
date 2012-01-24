

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines StoragePluginManager which loads and provides
access to StoragePlugins and their StorageResources"""

from configure.lib.storage_plugin.resource import StorageResource, ScannableResource
from configure.lib.storage_plugin.plugin import StoragePlugin
from configure.lib.storage_plugin.log import storage_plugin_log
from configure.models.storage_plugin import StoragePluginRecord, StorageResourceClassStatistic
from configure.models.storage_plugin import StorageResourceRecord, StorageResourceClass
from django.db import transaction


class LoadedResourceClass(object):
    """Convenience store of introspected information about StorageResource
       subclasses from loaded modules."""
    def __init__(self, resource_class, resource_class_id):
        self.resource_class = resource_class
        self.resource_class_id = resource_class_id


class LoadedPlugin(object):
    """Convenience store of introspected information about loaded
       plugin modules."""
    def __init__(self, plugin_manager, module, plugin_class):
        # Map of name string to class
        self.resource_classes = {}
        self.plugin_class = plugin_class
        self.plugin_record, created = StoragePluginRecord.objects.get_or_create(module_name = module)
        self.scannable_resource_classes = []

        for cls in plugin_class._resource_classes:
            # Populate database records for the classes
            vrc, created = StorageResourceClass.objects.get_or_create(
                    storage_plugin = self.plugin_record,
                    class_name = cls.__name__)
            for name, stat_obj in cls._storage_statistics.items():
                class_stat, created = StorageResourceClassStatistic.objects.get_or_create(
                        resource_class = vrc,
                        name = name)

            plugin_manager.resource_class_id_to_class[vrc.id] = cls
            self.resource_classes[cls.__name__] = LoadedResourceClass(cls, vrc.id)
            if issubclass(cls, ScannableResource):
                self.scannable_resource_classes.append(cls.__name__)


class StoragePluginManager(object):
    def __init__(self):
        self.loaded_plugins = {}
        self.plugin_sessions = {}

        self.resource_class_id_to_class = {}

        from settings import INSTALLED_STORAGE_PLUGINS
        for plugin in INSTALLED_STORAGE_PLUGINS:
            self.load_plugin(plugin)

    def get_resource_class_by_id(self, id):
        return self.resource_class_id_to_class[id]

    def get_scannable_resource_ids(self, plugin):
        loaded_plugin = self.loaded_plugins[plugin]
        records = StorageResourceRecord.objects.\
               filter(resource_class__storage_plugin = loaded_plugin.plugin_record).\
               filter(resource_class__class_name__in = loaded_plugin.scannable_resource_classes).\
               filter(parents = None).values('id')
        return [r['id'] for r in records]

    def get_scannable_resource_classes(self):
        class_records = []
        for k, v in self.loaded_plugins.items():
            class_records.extend(list(StorageResourceClass.objects.filter(
                storage_plugin = v.plugin_record,
                class_name__in = v.scannable_resource_classes)))

        return class_records

    @transaction.commit_on_success
    def create_root_resource(self, plugin_mod, resource_class_name, **kwargs):
        storage_plugin_log.debug("create_root_resource %s %s %s" % (plugin_mod, resource_class_name, kwargs))
        # Try to find the resource class in the plugin module
        resource_class, resource_class_id = self.get_plugin_resource_class(plugin_mod, resource_class_name)

        # Construct a record
        record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, kwargs)

        # XXX should we let people modify root records?  e.g. change the IP
        # address of a controller rather than deleting it, creating a new
        # one and letting the pplugin repopulate us with 'new' resources?
        # This will present the challenge of what to do with instances of
        # StorageResource subclasses which are already present in running plugins.

        storage_plugin_log.debug("create_root_resource created %d" % (record.id))
        return record.pk

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

        try:
            loaded_resource = loaded_plugin.resource_classes[resource_class_name]
        except KeyError:
            raise RuntimeError("Resource %s not found in %s (not one of %s)" % (
                resource_class_name, plugin_module, loaded_plugin.resource_classes.keys()))

        return loaded_resource.resource_class, loaded_resource.resource_class_id

    # FIXME: rename to get_all_resource_classes
    def get_all_resources(self):
        for plugin in self.loaded_plugins.values():
            for loaded_res in plugin.resource_classes.values():
                yield (loaded_res.resource_class_id, loaded_res.resource_class)

    def get_plugin_class(self, module):
        return self.loaded_plugins[module].plugin_class

    def _load_plugin(self, module_name, plugin_klass):
        storage_plugin_log.debug("_load_plugin %s %s" % (module_name, plugin_klass))
        self.loaded_plugins[module_name] = LoadedPlugin(self, module_name, plugin_klass)

    def load_plugin(self, module):
        """Load a StoragePlugin class from a module given a
           python path like 'configure.lib.lvm',
           or simply return it if it was already loaded.  Note that the
           StoragePlugin within the module will not be instantiated when this
           returns, caller is responsible for instantiating it.

           @return A subclass of StoragePlugin"""
        if module in self.loaded_plugins:
            raise RuntimeError("Duplicate storage plugin module %s" % module)

        # Load the module
        mod = __import__(module)
        components = module.split('.')
        plugin_name = module
        for comp in components[1:]:
            mod = getattr(mod, comp)
            plugin_name = comp
        plugin_module = mod

        # Find all StoragePlugin subclasses in the module
        plugin_klasses = []
        import inspect
        for name, cls in inspect.getmembers(plugin_module):
            if inspect.isclass(cls) and issubclass(cls, StoragePlugin) and cls != StoragePlugin:
                plugin_klasses.append(cls)

        # Make sure we have exactly one StoragePlugin subclass
        if len(plugin_klasses) > 1:
            raise RuntimeError("Module %s defines more than one StoragePlugin: %s!" % (module, plugin_klasses))
        elif len(plugin_klasses) == 0:
            raise RuntimeError("Module %s does not define a StoragePlugin!" % module)
        else:
            plugin_klass = plugin_klasses[0]

        # Hook in a logger to the StoragePlugin subclass
        import logging
        import os
        import settings
        log = logging.getLogger("storage_plugin_log_%s" % module)
        handler = logging.FileHandler(os.path.join(settings.LOG_PATH, 'storage_plugin.log'))
        handler.setFormatter(logging.Formatter("[%%(asctime)s: %%(levelname)s/%s] %%(message)s" % module, '%d/%b/%Y:%H:%M:%S'))
        log.addHandler(handler)
        if module in settings.STORAGE_PLUGIN_DEBUG_PLUGINS or settings.STORAGE_PLUGIN_DEBUG:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.WARNING)
        plugin_klass.log = log

        # Populate _resource_classes from all StorageResource in the same module
        # (or leave it untouched if the plugin author overrode it)
        if not hasattr(plugin_klass, '_resource_classes'):
            import inspect
            plugin_klass._resource_classes = []
            for name, cls in inspect.getmembers(plugin_module):
                if inspect.isclass(cls) and issubclass(cls, StorageResource) and cls != StorageResource:
                    plugin_klass._resource_classes.append(cls)

        self._load_plugin(plugin_name, plugin_klass)
        return plugin_klass


storage_plugin_manager = StoragePluginManager()
