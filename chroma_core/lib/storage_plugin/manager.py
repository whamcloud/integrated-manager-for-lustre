# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""This module defines StoragePluginManager which loads and provides
access to StoragePlugins and their StorageResources"""
import sys
import traceback

from django.conf import settings

from chroma_core.lib.storage_plugin.api import relations
from chroma_core.lib.storage_plugin.base_resource import (
    BaseStorageResource,
    BaseScannableResource,
    ResourceProgrammingError,
)

from chroma_core.lib.storage_plugin.base_plugin import BaseStoragePlugin
from chroma_core.lib.storage_plugin.log import storage_plugin_log
from chroma_core.lib.util import all_subclasses
from chroma_core.models.storage_plugin import StoragePluginRecord
from chroma_core.models.storage_plugin import StorageResourceRecord, StorageResourceClass


class PluginNotFound(Exception):
    def __str__(self):
        return "PluginNotFound: %s" % self.message


class PluginProgrammingError(Exception):
    pass


class VersionMismatchError(PluginProgrammingError):
    """Raised when a plugin is loaded that declares a different version.

    The version requested by the plugin is saved to the Error.
    """

    def __init__(self, version):
        self.version = version


class VersionNotFoundError(PluginProgrammingError):
    """Raised when a plugin doesn't declare a version attribute."""

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
        if not hasattr(plugin_class, "_resource_classes"):
            import inspect

            plugin_class._resource_classes = []
            for name, cls in inspect.getmembers(module):
                if inspect.isclass(cls) and issubclass(cls, BaseStorageResource) and cls != BaseStorageResource:
                    plugin_class._resource_classes.append(cls)

        # Map of name string to class
        self.resource_classes = {}
        self.plugin_class = plugin_class
        self.plugin_record, created = StoragePluginRecord.objects.get_or_create(module_name=module_name)
        if created:
            self.plugin_record.internal = plugin_class.internal
            self.plugin_record.save()

        self.scannable_resource_classes = []

        for cls in plugin_class._resource_classes:
            if not hasattr(cls._meta, "identifier"):
                raise ResourceProgrammingError(cls.__name__, "No Meta.identifier")

            # Populate database records for the classes
            vrc, created = StorageResourceClass.objects.get_or_create(
                storage_plugin=self.plugin_record, class_name=cls.__name__
            )
            if created:
                vrc.user_creatable = issubclass(cls, BaseScannableResource)
                vrc.save()

            plugin_manager.resource_class_id_to_class[vrc.id] = cls
            plugin_manager.resource_class_class_to_id[cls] = vrc.id
            self.resource_classes[cls.__name__] = LoadedResourceClass(cls, vrc.id)
            if issubclass(cls, BaseScannableResource):
                self.scannable_resource_classes.append(cls.__name__)


class StoragePluginManager(object):
    def __init__(self):
        self.loaded_plugins = {}
        self.errored_plugins = []

        self.resource_class_id_to_class = {}
        self.resource_class_class_to_id = {}

        from settings import INSTALLED_STORAGE_PLUGINS

        for plugin in INSTALLED_STORAGE_PLUGINS:
            try:
                self.load_plugin(plugin)
            except (ImportError, SyntaxError, ResourceProgrammingError, PluginProgrammingError) as e:
                storage_plugin_log.error("Failed to load plugin '%s': %s" % (plugin, traceback.format_exc()))
                self.errored_plugins.append((plugin, e))

        for id, klass in self.resource_class_id_to_class.items():
            klass._meta.relations = list(klass._meta.orig_relations)

        def can_satisfy_relation(klass, attributes):
            for attribute in attributes:
                if not attribute in klass._meta.storage_attributes:
                    return False

            return True

        for id, klass in self.resource_class_id_to_class.items():
            for relation in klass._meta.relations:
                # If ('linux', 'ScsiDevice') form was used, substitute the real class
                if isinstance(relation, relations.Provide):
                    if isinstance(relation.provide_to, tuple):
                        prov_klass, prov_klass_id = self.get_plugin_resource_class(*relation.provide_to)
                        relation.provide_to = prov_klass
                elif isinstance(relation, relations.Subscribe):
                    if isinstance(relation.subscribe_to, tuple):
                        sub_klass, sub_klass_id = self.get_plugin_resource_class(*relation.subscribe_to)
                        relation.subscribe_to = sub_klass

                # Generate reverse-Subscribe relations
                if isinstance(relation, relations.Provide):
                    # Synthesize Subscribe objects on the objects which might
                    # be on the receiving event of a Provide relation.  The original
                    # Provide object plays no further role.
                    subscription = relations.Subscribe(klass, relation.attributes, relation.ignorecase)
                    if can_satisfy_relation(relation.provide_to, relation.attributes):
                        relation.provide_to._meta.relations.append(subscription)
                    for sc in all_subclasses(relation.provide_to):
                        if can_satisfy_relation(sc, relation.attributes):
                            sc._meta.relations.append(subscription)

    @property
    def loaded_plugin_names(self):
        return self.loaded_plugins.keys()

    def get_errored_plugins(self):
        return [e[0] for e in self.errored_plugins]

    def get_resource_class_id(self, klass):
        try:
            return self.resource_class_class_to_id[klass]
        except KeyError:
            raise PluginNotFound("Looking for class %s" % klass.__name__)

    def get_resource_class_by_id(self, id):
        try:
            return self.resource_class_id_to_class[id]
        except KeyError:
            raise PluginNotFound("Looking for class id %s " % id)

    def get_scannable_resource_ids(self, plugin):
        loaded_plugin = self.loaded_plugins[plugin]
        records = (
            StorageResourceRecord.objects.filter(resource_class__storage_plugin=loaded_plugin.plugin_record)
            .filter(resource_class__class_name__in=loaded_plugin.scannable_resource_classes)
            .filter(parents=None)
            .values("id")
        )
        return [r["id"] for r in records]

    def get_resource_classes(self, scannable_only=False, show_internal=False):
        """Return a list of StorageResourceClass records

        :param scannable_only: Only report BaseScannableResource subclasses
        :param show_internal: Include plugins with the internal=True attribute (excluded by default)
        """
        class_records = []
        for k, v in self.loaded_plugins.items():
            if not show_internal and v.plugin_class.internal:
                continue

            filter = {}
            filter["storage_plugin"] = v.plugin_record
            if scannable_only:
                filter["class_name__in"] = v.scannable_resource_classes

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
            raise PluginNotFound("Plugin %s not found (not one of %s)" % (plugin_module, self.loaded_plugins.keys()))

        try:
            loaded_resource = loaded_plugin.resource_classes[resource_class_name]
        except KeyError:
            raise PluginNotFound(
                "Resource %s not found in %s (not one of %s)"
                % (resource_class_name, plugin_module, loaded_plugin.resource_classes.keys())
            )

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

    def validate_plugin(self, module):
        errors = []
        try:
            self.load_plugin(module)
        except ResourceProgrammingError as e:
            errors.append(e.__str__())
        except VersionNotFoundError as e:
            errors.append(
                "Add version=<int> to your plugin module. Consult "
                "Comand Center documentation for API version "
                "supported."
            )
        except VersionMismatchError as e:
            plugin_version = e.version
            command_center_version = settings.STORAGE_API_VERSION
            errors.append(
                "The plugin declares version %s. "
                "However, this manager server version supports "
                "version %s of the Plugin API." % (plugin_version, command_center_version)
            )
        except PluginProgrammingError as e:
            errors.append(e.__str__())
        except SyntaxError as e:
            errors.append("SyntaxError: %s:%s:%s: %s" % (e.filename, e.lineno, e.offset, e.text))
        except ImportError as e:
            errors.append(e.__str__())

        return errors

    def _validate_api_version(self, module):

        if not hasattr(module, "version"):
            raise VersionNotFoundError()

        if type(module.version) != int or settings.STORAGE_API_VERSION != module.version:
            raise VersionMismatchError(module.version)

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
            raise PluginProgrammingError("Duplicate storage plugin module %s" % module)

        if module in sys.modules:
            storage_plugin_log.warning("Reloading module %s (okay if testing)" % module)
            mod = sys.modules[module]
        else:
            # Load the module
            try:
                mod = __import__(module)
            except (ImportError, ResourceProgrammingError, SyntaxError) as e:
                storage_plugin_log.error("Error importing %s: %s" % (module, e))
                raise

        components = module.split(".")

        plugin_name = module
        for comp in components[1:]:
            mod = getattr(mod, comp)
            plugin_name = comp
        plugin_module = mod

        self._validate_api_version(plugin_module)

        # Find all BaseStoragePlugin subclasses in the module
        from chroma_core.lib.storage_plugin.api.plugin import Plugin

        plugin_klasses = []
        import inspect

        for name, cls in inspect.getmembers(plugin_module):
            if (
                inspect.isclass(cls)
                and issubclass(cls, BaseStoragePlugin)
                and cls != BaseStoragePlugin
                and cls != Plugin
            ):
                plugin_klasses.append(cls)

        # Make sure we have exactly one BaseStoragePlugin subclass
        if len(plugin_klasses) > 1:
            raise PluginProgrammingError(
                "Module %s defines more than one BaseStoragePlugin: %s!" % (module, plugin_klasses)
            )
        elif len(plugin_klasses) == 0:
            raise PluginProgrammingError("Module %s does not define a BaseStoragePlugin!" % module)
        else:
            plugin_klass = plugin_klasses[0]

        # Hook in a logger to the BaseStoragePlugin subclass
        if not plugin_klass._log:
            import logging
            import settings

            log = logging.getLogger("storage_plugin_log_%s" % module)
            if module in settings.STORAGE_PLUGIN_DEBUG_PLUGINS or settings.STORAGE_PLUGIN_DEBUG:
                log.setLevel(logging.DEBUG)
            else:
                log.setLevel(logging.WARNING)
            plugin_klass._log = log
            plugin_klass._log_format = "[%%(asctime)s: %%(levelname)s/%s] %%(message)s" % module
        else:
            storage_plugin_log.warning("Double load of %s (okay if testing)" % plugin_name)

        try:
            self._load_plugin(plugin_module, plugin_name, plugin_klass)
        except ResourceProgrammingError as e:
            storage_plugin_log.error("Error loading %s: %s" % (plugin_name, e))
            raise
        else:
            return plugin_klass


storage_plugin_manager = StoragePluginManager()
