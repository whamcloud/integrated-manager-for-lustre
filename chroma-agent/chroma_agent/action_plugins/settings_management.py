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


import os
import re
import json

from chroma_agent import config


def set_server_url(url):
    server_conf = dict(url = url)
    config.set('settings', 'server', server_conf)


def set_agent_config(key, val):
    agent_settings = config.get('settings', 'agent')
    agent_settings[key] = val
    config.update('settings', 'agent', agent_settings)


def get_agent_config(key):
    return config.get('settings', 'agent')[key]


def reset_agent_config():
    from chroma_agent import DEFAULT_AGENT_CONFIG
    config.update('settings', 'agent', DEFAULT_AGENT_CONFIG)


def _convert_agentstore_config():
    server_conf_path = os.path.join(config.path, 'server_conf')
    if os.path.exists(server_conf_path):
        with open(server_conf_path) as f:
            old_server_conf = json.load(f)
        config.set('settings', 'server', old_server_conf)
        os.unlink(server_conf_path)

    uuid_re = re.compile(r'[0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12}')
    for entry in os.listdir(config.path):
        if uuid_re.match(entry):
            target_conf_path = os.path.join(config.path, entry)
            with open(target_conf_path) as f:
                old_target_conf = json.load(f)
            config.set('targets', entry, old_target_conf)
            os.unlink(target_conf_path)


def convert_agent_config():
    # Ensure that even if we're upgrading from an older version, we have
    # a default agent config.
    if 'agent' not in config.sections:
        reset_agent_config()

    # < 2.1.0.0
    _convert_agentstore_config()


ACTIONS = [set_server_url, set_agent_config, get_agent_config, reset_agent_config, convert_agent_config]
