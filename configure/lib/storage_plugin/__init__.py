

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module provides functions to be used by storage hardware plugins
to hydra."""
from attributes import ResourceAttribute
from statistics import ResourceStatistic
from resource import StorageResource, GlobalId, ScannableResource
from plugin import StoragePlugin, ResourceNotFound
from manager import StoragePluginManager, storage_plugin_manager, ResourceQuery

