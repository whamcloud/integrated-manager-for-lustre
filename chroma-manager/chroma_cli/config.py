#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import os
from ConfigParser import SafeConfigParser

from chroma_cli.defaults import defaults, RC_FILES


class Configuration(object):
    """
    Simple key/val config store.  Acts mostly like a dict, encapsulates
    functionality for reading stored config from disk.

    For each configuration key, checks to see if a corresponding
    environment variable has been set, in which case the value of the
    environment variable supercedes the default value and config
    file value.

    Configuration values in order of precedence:
    default < ~/.chroma < os.getenv < argparse
    """
    def __init__(self, defaults=defaults):
        for key, val in self.read_user_config(defaults):
            env_val = os.getenv("CHROMA_%s" % key.upper())
            if env_val:
                setattr(self, key, env_val)
            else:
                setattr(self, key, val)

    def read_user_config(self, defaults=None, path=None):
        """
        Reads an .ini-style configuration file in the user's homedir
        (e.g. ~/.chroma):
        [chroma]
        api_url=http://some.other.host/api/
        username=foo
        password=bar
        """
        if path == None:
            candidates = (os.path.expanduser("~/%s" % f) for f in RC_FILES)
        else:
            candidates = path

        # TODO: We may need multi-section support, but let's keep it
        # simple for now.
        parser = SafeConfigParser(defaults)
        parser.add_section('chroma')
        parser.read(candidates)

        return parser.items('chroma')

    def update(self, other):
        self.__dict__.update(other)

    def __repr__(self):
        return "%s" % self.__dict__
