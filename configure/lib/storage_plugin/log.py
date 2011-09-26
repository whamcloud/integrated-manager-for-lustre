

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines a simple logger which is used by storage_plugin.* and 
provided for use by StoragePlugin subclasses"""

from logging import getLogger, DEBUG, WARNING, StreamHandler, FileHandler
import settings

storage_plugin_log = getLogger('storage_plugin_log')
storage_plugin_log.addHandler(FileHandler('storage_plugin.log'))
if settings.DEBUG:
    storage_plugin_log.setLevel(DEBUG)
    storage_plugin_log.addHandler(StreamHandler())
else:
    storage_plugin_log.setLevel(WARNING)
