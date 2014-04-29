# -*- coding: utf-8 -*-
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


import sys
import os

project_dir = None
pwd_parts = os.environ['PWD'].split(os.sep)
while not project_dir:
    settings_path = "/" + os.path.join(*(pwd_parts + ["settings.py"]))
    if os.path.exists(settings_path):
        project_dir = "/" + os.path.join(*pwd_parts)
    else:
        pwd_parts = pwd_parts[0:-1]
        if len(pwd_parts) == 0:
            raise RuntimeError("Can't find settings.py")

sys.path.append(project_dir)

agent_dir = os.path.join(*(list(os.path.split(project_dir)[0:-1]) + ['chroma-agent']))
sys.path.append(agent_dir)

from docs.conf_common import *

project = u'Intel® Manager for Lustre* software REST API'
master_doc = 'index'
