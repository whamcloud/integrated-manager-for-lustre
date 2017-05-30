#!/usr/bin/env python
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""This script substitutes production mode values into the nginx
configuration template, and outputs the configuration on stdout"""

import sys
from nginx_settings import get_production_nginx_settings

template_file = sys.argv[1]


config = open(template_file).read()
for setting, value in get_production_nginx_settings().items():
    config = config.replace("{{%s}}" % setting, str(value))

print config
