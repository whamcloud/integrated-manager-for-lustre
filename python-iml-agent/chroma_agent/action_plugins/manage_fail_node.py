# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_agent.lib.shell import AgentShell


def fail_node(args):
    # force a manual failover by failing a node
    AgentShell.try_run(["sync"])
    AgentShell.try_run(["sync"])
    AgentShell.try_run(["init", "0"])


ACTIONS = [fail_node]
CAPABILITIES = []
