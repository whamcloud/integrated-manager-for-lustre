#!/usr/bin/env python
# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""This script substitutes modifies supervisord.conf with production-specific settings"""


from ConfigParser import SafeConfigParser
import sys

base_config_file = sys.argv[1]

config = SafeConfigParser()
config.readfp(open(base_config_file, 'r'))

# Remove the nginx section, it is run as a separate init script in production
config.remove_section('program:nginx')

# Add production NODE_ENV
env = config.get('program:realtime', 'environment')
env = env + ',NODE_ENV="production"'
config.set('program:realtime', 'environment', env)

# Add production NODE_ENV
env = config.get('program:view_server', 'environment')
env = env + ',NODE_ENV="production"'
config.set('program:view_server', 'environment', env)

config.write(sys.stdout)
