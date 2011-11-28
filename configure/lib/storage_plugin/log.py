

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines a simple logger which is used by storage_plugin.* and
provided for use by StoragePlugin subclasses"""

import settings
import os

import logging
storage_plugin_log = logging.getLogger('storage_plugin_log')
handler = logging.FileHandler(os.path.join(settings.LOG_PATH, 'storage_plugin.log'))
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
storage_plugin_log.addHandler(handler)
if settings.DEBUG:
    storage_plugin_log.setLevel(logging.DEBUG)
    #handler = logging.StreamHandler()
    #handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
    #storage_plugin_log.addHandler(handler)
else:
    storage_plugin_log.setLevel(logging.WARNING)
