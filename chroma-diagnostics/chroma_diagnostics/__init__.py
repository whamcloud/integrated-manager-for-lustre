# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


try:
    from scm_version import VERSION, PACKAGE_VERSION, IS_RELEASE, BUILD
    __version__ = VERSION
    __package_version__ = PACKAGE_VERSION
    __build__ = BUILD
    __is_release__ = IS_RELEASE
except ImportError:
    # These are defaults, should loosely track latest dev tag, won't
    # work with packaging but will allow non-packaged installs to work
    # OK.
    __version__ = '1.99.0.0-dev'
    __package_version__ = __version__
    __build__ = 1
    __is_release__ = False


def package_version():
    return __package_version__


def version():
    return __version__
