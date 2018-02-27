# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import time
from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import daemon_log

def set_conf_param(key=None, value=None):
    if value is not None:
        result = AgentShell.run(['lctl', 'conf_param', "%s=%s" % (key, value)])
        i = 0
        while result.rc != 0 and i < 5:
            i += 1
            daemon_log.info("try %s: lctl conf_param %s=%s failed (%s).\n"
                            "stdout: %s\nstderr: %s" % (i, key, value,
                                                        result.rc,
                                                        result.stdout,
                                                        result.stderr))

            time.sleep(5)
            result = AgentShell.run(['lctl', 'conf_param', "%s=%s" % (key, value)])
        if result.rc != 0:
            raise RuntimeError("failed to lctl conf_param"
                               "%s=%s failed (%s)." % (key, value, result.rc))
    else:
        AgentShell.try_run(['lctl', 'conf_param', "-d", key])

ACTIONS = [set_conf_param]
CAPABILITIES = ['manage_conf_params']
