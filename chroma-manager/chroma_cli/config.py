#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os
from ConfigParser import SafeConfigParser

from chroma_cli.defaults import defaults, RC_FILES


class Configuration(object):
    """
    Simple key/val config store.  Acts mostly like a dict, encapsulates
    functionality for reading stored config from disk.
    """
    def __init__(self, defaults=defaults):
        for key, val in self.read_user_config(defaults):
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
