# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import os
import glob
import traceback
import collections

from chroma_agent.log import daemon_log
from iml_common.lib.agent_rpc import agent_error

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
        if not hasattr(cls, "_plugins"):
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

        names = set()

        assert os.path.isdir(path)
        for modfile in sorted(glob.glob("%s/*.py*" % path)):
            dir, filename = os.path.split(modfile)
            module = filename.split(".py")[0]
            if not module in EXCLUDED_PLUGINS:
                namespace = _build_namespace(dir)
                name = "%s.%s" % (namespace, module)
                names.add(name)

        return names

    @classmethod
    def _load_plugins(cls, names):
        """Given a list of plugin names, try to import them."""

        for name in names:
            try:
                try:
                    __import__(name, None, None)
                except ImportError as e:
                    if e.args[0].endswith(" " + name):
                        daemon_log.warn("** plugin %s not found" % name)
                    else:
                        raise
            except Exception:
                daemon_log.warn("** error loading plugin %s" % name)
                daemon_log.warn(traceback.format_exc())

    @classmethod
    def _find_plugins(cls):
        """Scan for plugins and load what's found into a list of plugin instances."""

        cls._load_plugins(cls._scan_plugins(cls.plugin_path))
        cls._plugins = {}
        for plugin_class in cls.plugin_class.__subclasses__():
            name = plugin_class.__module__.split(".")[-1]
            cls._plugins[name] = plugin_class


class DevicePlugin(object):
    """
    A plugin which maintains a state and sends and receives messages.
    """

    FAILSAFEDUPDATE = 60  # We always send an update every 60 cycles (60*10)seconds - 10 minutes.

    def __init__(self, session):
        self._session = session
        self._reset_delta()

        # When True the plugin should send an update to the manager regardless of whether any changes have occurred.
        # The plugin must reset to False when this is done.
        self.trigger_plugin_update = False

    def start_session(self):
        """
        Return information needed to start a manager-agent session, i.e. a full
        listing of all available information.

        :rtype: JSON-serializable object, DevicePluginMessage, or DevicePluginMessageCollection
        """
        raise NotImplementedError()

    def update_session(self):
        """
        Return information needed to maintain a manager-agent session, i.e. what
        has changed since the start of the session or since the last update.

        If you need to refer to any data from the start_session call, you can
        store it as an attribute on this DevicePlugin instance.

        This will never be called concurrently with respect to start_session, or
        before start_session.

        :rtype: JSON-serializable object, DevicePluginMessage, or DevicePluginMessageCollection
        """
        raise NotImplementedError()

    def teardown(self):
        """
        Stop and clean up any background resources such as threads
        """
        pass

    def on_message(self, body):
        """
        Handle a message sent from the manager (may be called concurrently with respect to
        start_session and update_session).
        """
        pass

    def send_message(self, body, callback=None):
        """
        Enqueue a message to be sent to the manager (returns immediately).

        If callback is set, it will be run after an attempt has been made to send the message to
        the manager.
        """
        if isinstance(body, DevicePluginMessage):
            self._session.send_message(body, callback)
        else:
            self._session.send_message(DevicePluginMessage(body), callback)

    def _delta_result(self, result, delta_fields=None):
        if not delta_fields:
            delta_fields = result.keys()

        if (self._safety_send < DevicePlugin.FAILSAFEDUPDATE) and (self.trigger_plugin_update is False):
            self._safety_send += 1

            for key in delta_fields:
                if result[key] == self.last_result[key]:  # If the result is not new then don't send it.
                    result[key] = None
                else:
                    self.last_result[key] = result[key]
        else:
            self._safety_send = 0
            self.trigger_plugin_update = False

        return result if result else None  # Turn {} into None, None will mean no message sent.

    def _reset_delta(self):
        self.last_result = collections.defaultdict(lambda: None)
        self._safety_send = 0


# For use with Queue.PriorityQueue (lower number is higher priority)
PRIO_LOW = 2
PRIO_NORMAL = 1
PRIO_HIGH = 0


class DevicePluginMessageCollection(list):
    """
    Zero or more messages from a device plugin, to be consumed one by one by a service on
    the manager server.

    Return this instead of a naked {} or a DevicePluginMessage if you need to return
    multiple messages from one callback.
    """

    def __init__(self, messages, priority=PRIO_NORMAL):
        """
        :param messages: An iterable of JSON-serializable objects
        :param priority: One of PRIO_LOW, PRIO_NORMAL, PRIO_HIGH
        """
        super(DevicePluginMessageCollection, self).__init__(messages)
        self.priority = priority


class DevicePluginMessage(object):
    """
    A single message from a device plugin, to be consumed by a service on the manager server.

    Return this instead of a naked {} if you need to set the priority.
    """

    def __init__(self, message, priority=PRIO_NORMAL):
        """
        :param message: A JSON-serializable object
        :param priority: One of PRIO_LOW, PRIO_NORMAL, PRIO_HIGH
        """
        self.message = message
        self.priority = priority


class DevicePluginManager(PluginManager):
    plugin_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "device_plugins")
    plugin_class = DevicePlugin

    def get(self, plugin_name):
        return self._plugins[plugin_name]


class ActionPluginManager(object):
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "action_plugins")
    commands = None
    capabilities = None

    # FIXME: duplication of code between ActionPluginManager and DevicePluginManager

    @classmethod
    def _load(cls):
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

        names = set()

        assert os.path.isdir(cls.path)
        for modfile in sorted(glob.glob("%s/*.py" % cls.path)):
            dir, filename = os.path.split(modfile)
            module = filename.split(".py")[0]
            if not module in EXCLUDED_PLUGINS:
                namespace = _build_namespace(dir)
                name = "%s.%s" % (namespace, module)
                names.add(name)

        daemon_log.info("Found action plugin modules: %s" % names)

        cls.commands = {}
        capabilities = set()
        for name in [n for n in names if not n.split(".")[-1].startswith("_")]:
            try:
                module = __import__(name, None, None, ["ACTIONS", "CAPABILITIES"])
                if hasattr(module, "ACTIONS"):
                    for fn in module.ACTIONS:
                        cls.commands[fn.func_name] = fn

                    daemon_log.info("Loaded actions from %s: %s" % (name, [fn.func_name for fn in module.ACTIONS]))
                else:
                    daemon_log.warning("No 'ACTIONS' defined in action module %s" % name)

                if hasattr(module, "CAPABILITIES") and module.CAPABILITIES:
                    capabilities.add(*module.CAPABILITIES)

            except Exception:
                daemon_log.warn("** error loading plugin %s" % name)
                daemon_log.warn(traceback.format_exc())

        cls.capabilities = list(capabilities)

    def __init__(self):
        if self.commands is None:
            self._load()

    def run(self, cmd, agent_daemon_context, args):
        # FIXME: provide a log object to action plugins that we capture
        # and send back to the caller
        try:
            fn = self.commands[cmd]
        except KeyError:
            return agent_error("Requested command %s was unknown to the agent" % cmd)

        # Only pass in the agent_daemon_context if the agent_daemon_context is expected by the function.
        # This feature was added just prior to 3.1 and whilst it would be better to always pass the context the
        # scope of the change was prohibitive at that time.
        # Not a fixme because it is of little value to make the additional changes at this time.
        if "agent_daemon_context" in fn.__code__.co_varnames:
            return fn(agent_daemon_context, **args)

        return fn(**args)
