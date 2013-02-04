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

SOCK_PATH = '/var/lib/chroma/supervisord.sock'

# Add sections to enable XMLRPC over a UNIX socket
config.add_section('unix_http_server')
config.set('unix_http_server', 'file', SOCK_PATH)
config.add_section('supervisorctl')
config.set('supervisorctl', 'serverurl', 'unix://%s' % SOCK_PATH)

config.write(sys.stdout)
