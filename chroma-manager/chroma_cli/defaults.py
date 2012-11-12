#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


# These aren't user-configurable, but this is a handy place to stash them.
RC_FILES = [".chroma", ".chromarc"]
PROXY_VARIABLES = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']

defaults = dict()

defaults['api_url'] = "http://localhost/api/"
defaults['username'] = ""
defaults['password'] = ""
defaults['output'] = "human"
defaults['nowait'] = False
defaults['noproxy'] = False
defaults['force'] = False
