# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import errno
import os

DEFAULT_AGENT_CONFIG = {
    'lustre_client_root': "/mnt/lustre_clients",
    'copytool_fifo_directory': "/var/spool",
    'copytool_template': "--quiet --update-interval %(report_interval)s --event-fifo %(event_fifo)s --archive %(archive_number)s %(hsm_arguments)s %(mountpoint)s"
}

PRODUCTION_CONFIG_STORE = "/var/lib/chroma"
DEVEL_CONFIG_STORE = os.path.join(os.path.dirname(__file__), ".dev_config_store")
from config_store import ConfigStore
try:
    config = ConfigStore(PRODUCTION_CONFIG_STORE)
except OSError as e:
    if e.errno == errno.EACCES:
        config = ConfigStore(DEVEL_CONFIG_STORE)
    else:
        raise

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
