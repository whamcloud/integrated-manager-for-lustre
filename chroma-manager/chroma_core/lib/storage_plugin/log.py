#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


"""This module defines a simple logger which is used by storage_plugin.* and
provided for use by BaseStoragePlugin subclasses"""


from chroma_core.services import log_register
storage_plugin_log = log_register('storage_plugin')
