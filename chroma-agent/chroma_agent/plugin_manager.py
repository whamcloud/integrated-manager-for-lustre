#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import os
import glob
import traceback
from chroma_agent.log import daemon_log

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
            name = plugin_class.__module__.split('.')[-1]
            cls._plugins[name] = plugin_class


class DevicePlugin(object):
    """
    A plugin which maintains a state and sends and receives messages.
    """

    def __init__(self, session):
        self._session = session

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

    def send_message(self, body, callback = None):
        """
        Enqueue a message to be sent to the manager (returns immediately).

        If callback is set, it will be run after an attempt has been made to send the message to
        the manager.
        """
        if isinstance(body, DevicePluginMessage):
            self._session.send_message(body, callback)
        else:
            self._session.send_message(DevicePluginMessage(body), callback)


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
    def __init__(self, messages, priority = PRIO_NORMAL):
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
    def __init__(self, message, priority = PRIO_NORMAL):
        """
        :param message: A JSON-serializable object
        :param priority: One of PRIO_LOW, PRIO_NORMAL, PRIO_HIGH
        """
        self.message = message
        self.priority = priority


class DevicePluginManager(PluginManager):
    plugin_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'device_plugins')
    plugin_class = DevicePlugin

    def get(self, plugin_name):
        return self._plugins[plugin_name]


class ActionPluginManager(object):
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'action_plugins')
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

        names = []

        assert os.path.isdir(cls.path)
        for modfile in sorted(glob.glob("%s/*.py" % cls.path)):
            dir, filename = os.path.split(modfile)
            module = filename.split(".py")[0]
            if not module in EXCLUDED_PLUGINS:
                namespace = _build_namespace(dir)
                name = "%s.%s" % (namespace, module)
                names.append(name)

        daemon_log.info("Found action plugin modules: %s" % names)

        cls.commands = {}
        capabilities = set()
        for name in [n for n in names if not n.split(".")[-1].startswith('_')]:
            try:
                module = __import__(name, None, None, ['ACTIONS', 'CAPABILITIES'])
                if hasattr(module, 'ACTIONS'):
                    for fn in module.ACTIONS:
                        cls.commands[fn.func_name] = fn

                    daemon_log.info("Loaded actions from %s: %s" % (name, [fn.func_name for fn in module.ACTIONS]))
                else:
                    daemon_log.warning("No 'ACTIONS' defined in action module %s" % name)

                if hasattr(module, 'CAPABILITIES') and module.CAPABILITIES:
                    capabilities.add(*module.CAPABILITIES)

            except Exception:
                daemon_log.warn("** error loading plugin %s" % name)
                daemon_log.warn(traceback.format_exc())

        cls.capabilities = list(capabilities)

    def __init__(self):
        if self.commands is None:
            self._load()

    def run(self, cmd, args):
        # FIXME: provide a log object to action plugins that we capture
        # and send back to the caller
        try:
            fn = self.commands[cmd]
        except KeyError:
            raise RuntimeError("Unknown command %s" % cmd)

        return fn(**args)
