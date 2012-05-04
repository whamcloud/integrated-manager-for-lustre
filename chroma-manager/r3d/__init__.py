#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


__version__ = '0.3.0'
__version_info__ = tuple([int(num) for num in __version__.split('.')])

# Enables copious amounts of debugging spew.
DEBUG = False

# By default, R3D will fill holes with the latest datapoint when catching up.
# Setting EMPTY_GAPS will prevent this behavior.
EMPTY_GAPS = True
