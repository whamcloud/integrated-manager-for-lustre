#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


try:
        from production_version import VERSION, BUILD, IS_RELEASE
        __version__ = VERSION
        __build__ = BUILD
        __is_release__ = IS_RELEASE
except ImportError:
        __version__ = '0.4.0'
        __build__ = 'dev'
        __is_release__ = False


def version():
    return __version__
