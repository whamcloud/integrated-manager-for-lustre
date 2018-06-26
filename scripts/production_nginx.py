#!/usr/bin/env python

# Copyright (c) 2018 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import sys
import settings

template_file = sys.argv[1]


nginx_settings = [
    'APP_PATH', 'REPO_PATH', 'HTTP_FRONTEND_PORT', 'HTTPS_FRONTEND_PORT',
    'HTTP_AGENT_PORT', 'HTTP_API_PORT', 'REALTIME_PORT', 'VIEW_SERVER_PORT',
    'SSL_PATH', 'DEVICE_AGGREGATOR_PORT'
]

config = open(template_file).read()
for setting in nginx_settings:
    config = config.replace("{{%s}}" % setting, str(getattr(settings, setting)))

print config
