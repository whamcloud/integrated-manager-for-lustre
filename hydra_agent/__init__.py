# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

__version__ = '0.3.0'
__version_info__ = tuple([int(num) for num in __version__.split('.')])


def version():
    return __version__
