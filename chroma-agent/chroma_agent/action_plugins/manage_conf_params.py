# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_agent.lib.shell import AgentShell


def set_conf_param(key = None, value = None):
    if value is not None:
        AgentShell.try_run(['lctl', 'conf_param', "%s=%s" % (key, value)])
    else:
        AgentShell.try_run(['lctl', 'conf_param', "-d", key])

ACTIONS = [set_conf_param]
CAPABILITIES = ['manage_conf_params']
