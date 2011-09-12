

# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

"""This module defines a simple logger which is used by storage_plugin.* and 
provided for use by VendorPlugin subclasses"""

from logging import getLogger, DEBUG, WARNING, StreamHandler, FileHandler
import settings

vendor_plugin_log = getLogger('vendor_plugin_log')
vendor_plugin_log.addHandler(FileHandler('vendor_plugin.log'))
if settings.DEBUG:
    vendor_plugin_log.setLevel(DEBUG)
    vendor_plugin_log.addHandler(StreamHandler())
else:
    vendor_plugin_log.setLevel(WARNING)
