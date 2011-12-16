

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines a simple logger which is used by storage_plugin.* and
provided for use by StoragePlugin subclasses"""

import settings
storage_plugin_log = settings.setup_log('storage_plugin')
