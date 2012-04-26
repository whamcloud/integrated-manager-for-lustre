#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os
import glob
import traceback
from chroma_agent.log import agent_log

EXCLUDED_PLUGINS = []


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
    """
    A plugin for monitoring something on the server, for example for detecting
    and monitoring a particular type of device.
    """
    def start_session(self):
        """
        Return information needed to start a manager-agent session, i.e. a full
        listing of all available information.

        :rtype: JSON-serializable object, typically a dict
        """
        raise NotImplementedError()

    def update_session(self):
        """
        Return information needed to maintain a manager-agent session, i.e. what
        has changed since the start of the session or since the last update.

        If you need to refer to any data from the start_session call, you can
        store it as an attribute on this DevicePlugin instance.

        :rtype: JSON-serializable object, typically a dict
        """
        raise NotImplementedError()


class ActionPlugin(object):
    """
    A plugin for performing a set of related actions on the server, for example
    performing operations on a particular type of device.
    """
    def register_commands(self, parser):
        """
        Define command line actions offered by this plugin.

        :param parser: An argparse.ArgumentParser
        :rtype: None
        """
        raise NotImplementedError()

    def capabilities(self):
        """
        Returns a list of capabilities advertised by this plugin.

        The default here is to simply return
        the parent module name (e.g. manage_targets).  This can
        be overridden by subclasses if the default is nonsensical.

        Optional for subclasses.
        """
        return [self.__class__.__module__.split('.')[-1]]


class DevicePluginManager(PluginManager):
    plugin_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'device_plugins')
    plugin_class = DevicePlugin


class ActionPluginManager(PluginManager):
    plugin_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'action_plugins')
    plugin_class = ActionPlugin
