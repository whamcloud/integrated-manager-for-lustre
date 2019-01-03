# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_cli.api import DEFAULT_API_URL


# These aren't user-configurable, but this is a handy place to stash them.
RC_FILES = [".chroma", ".chromarc"]
PROXY_VARIABLES = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]

defaults = dict()

defaults["api_url"] = DEFAULT_API_URL
defaults["username"] = ""
defaults["password"] = ""
defaults["output"] = "human"
defaults["nowait"] = False
defaults["noproxy"] = False
defaults["force"] = False
