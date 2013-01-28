#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


"""This script substitutes production mode values into the apache
configuration template, and outputs the configuration on stdout"""

import sys

template_file = sys.argv[1]

production_settings = {
    "app": "/usr/share/chroma-manager",
    "HTTP_FRONTEND_PORT": "80",
    "HTTPS_FRONTEND_PORT": "443",
    "HTTP_AGENT_PORT": "8002",
    "HTTP_API_PORT": "8001",
    "ssl": "/var/lib/chroma"
}

config = open(template_file).read()
for setting, value in production_settings.items():
    config = config.replace("{{%s}}" % setting, value)

print config
