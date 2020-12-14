# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.
try:
    from scm_version import VERSION, PACKAGE_VERSION, IS_RELEASE, BUILD

    __version__ = VERSION
    __package_version__ = PACKAGE_VERSION
    __build__ = BUILD
    __is_release__ = IS_RELEASE
except ImportError:
    from pkginfo import UnpackedSDist

    pkg = UnpackedSDist(".")
    __version__ = pkg.version
    __package_version__ = __version__
    __build__ = 1
    __is_release__ = False


def package_version():
    return __package_version__


def version():
    return __version__
