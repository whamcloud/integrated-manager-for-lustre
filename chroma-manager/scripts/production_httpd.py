#!/usr/bin/env python
#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
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


"""This script substitutes production mode values into the apache
configuration template, and outputs the configuration on stdout"""

import sys

template_file = sys.argv[1]

production_settings = {
    "app": "/usr/share/chroma-manager",
    "REPO_PATH": "/var/lib/chroma/repo",
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
