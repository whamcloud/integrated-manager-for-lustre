#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


__version__ = '0.3.3'
__version_info__ = tuple([int(num) for num in __version__.split('.')])


def version():
    return __version__
