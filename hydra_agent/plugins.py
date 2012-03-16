# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""
Simple plugin framework with minimal boilerplate required.  Uses introspection
to find subclasses of ActionPlugin and registers them as CLI subcommands.
"""

import os
import glob
import itertools
import traceback
from hydra_agent.log import agent_log

DEFAULT_PLUGINS = []
DEFAULT_SEARCH = [os.path.join(os.path.abspath(os.path.dirname(__file__)), 'actions')]
EXCLUDED_PLUGINS = []
# Singleton-ish hack for plugins
_instances = {}


class DevicePlugin(object):
    def annotate_block_device(info):
        return info

    def initial_scan(self):
        raise NotImplementedError()

    def update_scan(self):
        raise NotImplementedError()

# The 'linux' plugin scans block devices
# It can give you some per-plugin additional information
# for each one.
# This additional information is passed to the plugin's server
# side component.
# The server side component receives this information and synthesizes
# resources which link the block device to the controller

#class DdnDevicePlugin(object):
#    def annotate_block_device(info):
#        # Special case for DDN 10KE which correlates volumes via
#        # their 'OID' identifier and publishes this ID in /sys/block
#        # FIXME: find a way to shift this into the DDN plugin
#        oid_path = os.path.join("/sys/block", device_name, 'oid')
#        if os.path.exists(oid_path):
#            serial = open(oid_path, 'r').read().strip()


#class LinuxDevicePlugin(object):
#   def start_session(self, request, session):
#       from hydra_agent.actions.device_scan import device_scan
#       return device_scan()
#
#   def update_session(self, request, session):
#       return None

#
#class DevicePluginManager(object):
#   @classmethod
#    def annotate_block_device(info):
#        """For plugins which just need to help Chroma correlate
#        block devices between controllers and servers, it may be
#        sufficient to receive a callback for each block device,
#        and insert additional information such as a proprietary
#        device identifier"""
#
#    @classmethod
#    def request_handler(self, plugin_name, request, session):
#        LinuxDevicePlugin().request_handler(request, session)
#

class ActionPlugin(object):
    def capabilities(self):
        """Returns a list of capabilities advertised by this plugin."""
        # As a ridiculous hack, the default here is to simply return
        # the parent module name (e.g. manage_targets).  This can
        # be overridden by subclasses if the default is nonsensical.
        return [self.__class__.__module__.split('.')[-1]]


def scan_plugins(paths=()):
    """Builds a list of plugin names from a given set of paths."""

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

    for path in itertools.chain(paths, DEFAULT_SEARCH):
        if not os.path.isdir(path):
            continue

        for modfile in sorted(glob.glob("%s/*.py" % path)):
            dir, filename = os.path.split(modfile)
            module = filename.split(".py")[0]
            if not module in EXCLUDED_PLUGINS:
                namespace = _build_namespace(dir)
                name = "%s.%s" % (namespace, module)
                names.append(name)

    return names


def load_plugins(names=()):
    """Given a list of plugin names, try to import them."""

    for modname in itertools.chain(names, DEFAULT_PLUGINS):
        try:
            try:
                __import__(modname, None, None)
            except ImportError, e:
                if e.args[0].endswith(" " + modname):
                    agent_log.warn("** plugin %s not found" % modname)
                else:
                    raise
        except:
            agent_log.warn("** error loading plugin %s" % modname)
            agent_log.warn(traceback.format_exc())


def find_plugins():
    """Scan for plugins and load what's found into a list of plugin instances."""

    load_plugins(scan_plugins())
    plugins = []
    for cls in ActionPlugin.__subclasses__():
        # We only want one instance per plugin class.
        if cls not in _instances:
            _instances[cls] = cls()
        plugins.append(_instances[cls])
    return plugins
