#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os
import glob
import traceback
from chroma_agent.log import agent_log

EXCLUDED_PLUGINS = []

#class DdnDevicePlugin(object):
#    def annotate_block_device(info):
#        # Special case for DDN 10KE which correlates volumes via
#        # their 'OID' identifier and publishes this ID in /sys/block
#        # FIXME: find a way to shift this into the DDN plugin
#        oid_path = os.path.join("/sys/block", device_name, 'oid')
#        if os.path.exists(oid_path):
#            serial = open(oid_path, 'r').read().strip()


class PluginManager(object):
    """
    Simple plugin framework with minimal boilerplate required.  Uses introspection
    to find subclasses of plugin_class in plugin_path.
    """
    plugin_path = None
    plugin_class = None

    @classmethod
    def get_plugins(cls):
        if not hasattr(cls, '_plugins'):
            cls._find_plugins()

        return cls._plugins

    @classmethod
    def _scan_plugins(cls, path):
        """Builds a list of plugin module names from a path"""

        def _walk_parents(dir):
            """Walk backwards up the tree to first non-module directory."""
            components = []

            if os.path.isfile("%s/__init__.py" % dir):
                parent, child = os.path.split(dir)
                components.append(child)
                components.extend(_walk_parents(parent))

            return components

        def _build_namespace(dir):
            """Builds a namespace by finding all parent modules."""
            return ".".join(reversed(_walk_parents(dir)))

        names = []

        assert os.path.isdir(path)
        for modfile in sorted(glob.glob("%s/*.py" % path)):
            dir, filename = os.path.split(modfile)
            module = filename.split(".py")[0]
            if not module in EXCLUDED_PLUGINS:
                namespace = _build_namespace(dir)
                name = "%s.%s" % (namespace, module)
                names.append(name)

        return names

    @classmethod
    def _load_plugins(cls, names):
        """Given a list of plugin names, try to import them."""

        for name in names:
            try:
                try:
                    __import__(name, None, None)
                except ImportError, e:
                    if e.args[0].endswith(" " + name):
                        agent_log.warn("** plugin %s not found" % name)
                    else:
                        raise
            except:
                agent_log.warn("** error loading plugin %s" % name)
                agent_log.warn(traceback.format_exc())

    @classmethod
    def _find_plugins(cls):
        """Scan for plugins and load what's found into a list of plugin instances."""

        cls._load_plugins(cls._scan_plugins(cls.plugin_path))
        cls._plugins = {}
        for plugin_class in cls.plugin_class.__subclasses__():
            name = plugin_class.__module__.split('.')[-1]
            cls._plugins[name] = plugin_class


class DevicePlugin(object):
    def start_session(self):
        raise NotImplementedError()

    def update_session(self):
        raise NotImplementedError()


class ActionPlugin(object):
    def capabilities(self):
        """Returns a list of capabilities advertised by this plugin."""
        # The default here is to simply return
        # the parent module name (e.g. manage_targets).  This can
        # be overridden by subclasses if the default is nonsensical.
        return [self.__class__.__module__.split('.')[-1]]


class DevicePluginManager(PluginManager):
    plugin_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'device_plugins')
    plugin_class = DevicePlugin


class ActionPluginManager(PluginManager):
    plugin_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'action_plugins')
    plugin_class = ActionPlugin
