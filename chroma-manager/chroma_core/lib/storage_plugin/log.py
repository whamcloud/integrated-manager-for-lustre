#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


"""This module defines a simple logger which is used by storage_plugin.* and
provided for use by BaseStoragePlugin subclasses"""

import settings
storage_plugin_log = settings.setup_log('storage_plugin')
