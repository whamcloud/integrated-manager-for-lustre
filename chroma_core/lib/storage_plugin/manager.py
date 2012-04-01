

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines StoragePluginManager which loads and provides
access to StoragePlugins and their StorageResources"""
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource, ScannableResource

from chroma_core.lib.storage_plugin.base_plugin import BaseStoragePlugin
from chroma_core.lib.storage_plugin.log import storage_plugin_log
from chroma_core.models.storage_plugin import StoragePluginRecord, StorageResourceClassStatistic
from chroma_core.models.storage_plugin import StorageResourceRecord, StorageResourceClass


class PluginNotFound(Exception):
    pass


class LoadedResourceClass(object):
    """Convenience store of introspected information about BaseStorageResource
       subclasses from loaded modules."""
    def __init__(self, resource_class, resource_class_id):
        self.resource_class = resource_class
        self.resource_class_id = resource_class_id


class LoadedPlugin(object):
    """Convenience store of introspected information about loaded
       plugin modules."""
    def __init__(self, plugin_manager, module, module_name, plugin_class):
        # Populate _resource_classes from all BaseStorageResource in the same module
        # (or leave it untouched if the plugin author overrode it)
        if not hasattr(plugin_class, '_resource_classes'):
            import inspect
            plugin_class._resource_classes = []
            for name, cls in inspect.getmembers(module):
                if inspect.isclass(cls) and issubclass(cls, BaseStorageResource) and cls != BaseStorageResource:
                    storage_plugin_log.debug("recognized class %s %s" % (name, cls))
                    plugin_class._resource_classes.append(cls)
                else:
                    storage_plugin_log.debug("ignoring class %s %s" % (name, cls))

        # Map of name string to class
        self.resource_classes = {}
        self.plugin_class = plugin_class
        self.plugin_record, created = StoragePluginRecord.objects.get_or_create(module_name = module_name)
        if created:
            self.plugin_record.internal = plugin_class.internal
            self.plugin_record.save()

        self.scannable_resource_classes = []

        for cls in plugin_class._resource_classes:
            # Populate database records for the classes
            vrc, created = StorageResourceClass.objects.get_or_create(
                    storage_plugin = self.plugin_record,
                    class_name = cls.__name__)
            if created:
                vrc.user_creatable = issubclass(cls, ScannableResource)
                vrc.save()
            for name, stat_obj in cls._storage_statistics.items():
                class_stat, created = StorageResourceClassStatistic.objects.get_or_create(
                        resource_class = vrc,
                        name = name)

            plugin_manager.resource_class_id_to_class[vrc.id] = cls
            plugin_manager.resource_class_class_to_id[cls] = vrc.id
            self.resource_classes[cls.__name__] = LoadedResourceClass(cls, vrc.id)
            if issubclass(cls, ScannableResource):
                self.scannable_resource_classes.append(cls.__name__)


class StoragePluginManager(object):
    def __init__(self):
        self.loaded_plugins = {}

        self.resource_class_id_to_class = {}
        self.resource_class_class_to_id = {}

        from settings import INSTALLED_STORAGE_PLUGINS
        for plugin in INSTALLED_STORAGE_PLUGINS:
            self.load_plugin(plugin)

    def get_resource_class_id(self, klass):
        try:
            return self.resource_class_class_to_id[klass]
        except KeyError:
            raise PluginNotFound()

    def get_resource_class_by_id(self, id):
        try:
            return self.resource_class_id_to_class[id]
        except KeyError:
            raise PluginNotFound()

    def get_scannable_resource_ids(self, plugin):
        loaded_plugin = self.loaded_plugins[plugin]
        records = StorageResourceRecord.objects.\
               filter(resource_class__storage_plugin = loaded_plugin.plugin_record).\
               filter(resource_class__class_name__in = loaded_plugin.scannable_resource_classes).\
               filter(parents = None).values('id')
        return [r['id'] for r in records]

    def get_resource_classes(self, scannable_only = False, show_internal = False):
        """Return a list of StorageResourceClass records

           :param scannable_only: Only report ScannableResource subclasses
           :param show_internal: Include plugins with the internal=True attribute (excluded by default)
        """
        class_records = []
        for k, v in self.loaded_plugins.items():
            if not show_internal and v.plugin_class.internal:
                continue

            filter = {}
            filter['storage_plugin'] = v.plugin_record
            if scannable_only:
                filter['class_name__in'] = v.scannable_resource_classes

            class_records.extend(list(StorageResourceClass.objects.filter(**filter)))

        return class_records

    def register_plugin(self, plugin_instance):
        """Register a particular instance of a BaseStoragePlugin"""
        # FIXME: session ID not really used for anything, it's a vague
        # nod to the future remote-run plugins.
        session_id = plugin_instance.__class__.__name__

        storage_plugin_log.info("Registered plugin instance %s with id %s" % (plugin_instance, session_id))
        return session_id

    def get_plugin_resource_class(self, plugin_module, resource_class_name):
        """Return a BaseStorageResource subclass"""
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
        try:
            return self.loaded_plugins[module].plugin_class
        except KeyError:
            raise PluginNotFound(module)

    def _load_plugin(self, module, module_name, plugin_klass):
        storage_plugin_log.debug("_load_plugin %s %s" % (module_name, plugin_klass))
        self.loaded_plugins[module_name] = LoadedPlugin(self, module, module_name, plugin_klass)

    def load_plugin(self, module):
        """Load a BaseStoragePlugin class from a module given a
           python path like chroma_core.lib.lvm',
           or simply return it if it was already loaded.  Note that the
           BaseStoragePlugin within the module will not be instantiated when this
           returns, caller is responsible for instantiating it.

           @return A subclass of BaseStoragePlugin"""
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

        # Find all BaseStoragePlugin subclasses in the module
        from chroma_core.lib.storage_plugin.api.plugin import Plugin
        plugin_klasses = []
        import inspect
        for name, cls in inspect.getmembers(plugin_module):
            if inspect.isclass(cls) and issubclass(cls, BaseStoragePlugin) and cls != BaseStoragePlugin and cls != Plugin:
                plugin_klasses.append(cls)

        # Make sure we have exactly one BaseStoragePlugin subclass
        if len(plugin_klasses) > 1:
            raise RuntimeError("Module %s defines more than one BaseStoragePlugin: %s!" % (module, plugin_klasses))
        elif len(plugin_klasses) == 0:
            raise RuntimeError("Module %s does not define a BaseStoragePlugin!" % module)
        else:
            plugin_klass = plugin_klasses[0]

        # Hook in a logger to the BaseStoragePlugin subclass
        import logging
        import logging.handlers
        import os
        import settings
        log = logging.getLogger("storage_plugin_log_%s" % module)
        handler = logging.handlers.WatchedFileHandler(os.path.join(settings.LOG_PATH, 'storage_plugin.log'))
        handler.setFormatter(logging.Formatter("[%%(asctime)s: %%(levelname)s/%s] %%(message)s" % module, '%d/%b/%Y:%H:%M:%S'))
        log.addHandler(handler)
        if module in settings.STORAGE_PLUGIN_DEBUG_PLUGINS or settings.STORAGE_PLUGIN_DEBUG:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.WARNING)
        plugin_klass.log = log

        self._load_plugin(plugin_module, plugin_name, plugin_klass)
        return plugin_klass


storage_plugin_manager = StoragePluginManager()
