#!/usr/bin/env python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


"""This script substitutes modifies supervisord.conf with production-specific settings"""


from ConfigParser import ConfigParser
import sys

base_config_file = sys.argv[1]

config = ConfigParser()
config.readfp(open(base_config_file, 'r'))

# Remove the apache section, it is run as a separate init script in production
config.remove_section('program:httpd')

config.write(sys.stdout)
