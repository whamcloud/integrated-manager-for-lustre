#!/usr/bin/env python
#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


"""This script substitutes modifies supervisord.conf with production-specific settings"""


from ConfigParser import SafeConfigParser
import sys

base_config_file = sys.argv[1]

config = SafeConfigParser()
config.readfp(open(base_config_file, 'r'))

# Remove the nginx section, it is run as a separate init script in production
config.remove_section('program:nginx')

# Replace the primus section argument to indicate it's running in production
command = config.get('program:primus', 'command')
new_command = command.replace('--type=dev', '--type=prod')
config.set('program:primus', 'command', new_command)

# Add production NODE_ENV
env = config.get('program:view_server', 'environment')
env = env + ',NODE_ENV="production"'
config.set('program:view_server', 'environment', env)

config.write(sys.stdout)
