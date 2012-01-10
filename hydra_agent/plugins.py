# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""
Simple plugin framework with minimal boilerplate required.  Uses introspection
to find subclasses of AgentPlugin and registers them as CLI subcommands.
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


class AgentPlugin(object):
    pass


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
    for cls in AgentPlugin.__subclasses__():
        # We only want one instance per plugin class.
        if cls not in _instances:
            _instances[cls] = cls()
        plugins.append(_instances[cls])
    return plugins
