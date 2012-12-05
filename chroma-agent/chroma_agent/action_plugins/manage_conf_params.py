#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.shell import try_run


def set_conf_param(key = None, value = None):
    if value:
        try_run(['lctl', 'conf_param', "%s=%s" % (key, value)])
    else:
        try_run(['lctl', 'conf_param', "-d", key])

ACTIONS = [set_conf_param]
CAPABILITIES = ['manage_conf_params']
