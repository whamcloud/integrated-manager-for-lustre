# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import errno
import os

DEFAULT_AGENT_CONFIG = {
    "lustre_client_root": "/mnt/lustre_clients",
}

PRODUCTION_CONFIG_STORE = "/var/lib/chroma"
DEVEL_CONFIG_STORE = os.path.join(os.path.dirname(__file__), ".dev_config_store")
from .config_store import ConfigStore

try:
    config = ConfigStore(PRODUCTION_CONFIG_STORE)
except OSError as e:
    if e.errno == errno.EACCES:
        config = ConfigStore(DEVEL_CONFIG_STORE)
    else:
        raise

try:
    from .version import VERSION, PACKAGE_VERSION

    __version__ = VERSION
    __package_version__ = PACKAGE_VERSION
except ImportError:
    from pkginfo import UnpackedSDist

    pkg = UnpackedSDist(".")
    __version__ = pkg.version
    __package_version__ = __version__


def package_version():
    return __package_version__


def version():
    return __version__
