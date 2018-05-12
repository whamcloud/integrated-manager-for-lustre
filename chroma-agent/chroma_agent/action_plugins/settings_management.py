# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import os
import re
import json

from chroma_agent import utils
from chroma_agent import config
from chroma_agent.config_store import ConfigKeyExistsError


def set_profile(profile_json):
    profile = json.loads(profile_json)

    try:
        config.set('settings', 'profile', profile)
    except ConfigKeyExistsError:
        config.update('settings', 'profile', profile)


def set_agent_config(key, val):
    agent_settings = config.get('settings', 'agent')
    agent_settings[key] = val
    config.update('settings', 'agent', agent_settings)


def get_agent_config(key):
    return config.get('settings', 'agent')[key]


def migrate_file(old_path, new_path):
    if os.path.exists(old_path):
        os.rename(old_path, new_path)

def reset_agent_config():
    from chroma_agent import DEFAULT_AGENT_CONFIG
    config.update('settings', 'agent', DEFAULT_AGENT_CONFIG)


def _convert_agentstore_config():
    server_conf_path = os.path.join(config.path, 'server_conf')
    if os.path.exists(server_conf_path):
        with open(server_conf_path) as f:
            old_server_conf = json.load(f)
        utils.set_server_url(old_server_conf.url)
        os.unlink(server_conf_path)

    try:
        url = config.get('settings', 'server').get('url')
        utils.set_server_url(url)

        config.delete('settings', 'server')
    except (KeyError, TypeError):
        pass

    crypto_files = map(
        lambda x: (os.path.join(config.path, x), os.path.join('/etc/iml', x)),
        ['authority.crt', 'private.pem', 'self.crt'])

    map(lambda x: migrate_file(*x), crypto_files)

    uuid_re = re.compile(
        r'[0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12}')
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


ACTIONS = [
    utils.set_server_url, set_agent_config, set_profile, get_agent_config,
    reset_agent_config, convert_agent_config
]
