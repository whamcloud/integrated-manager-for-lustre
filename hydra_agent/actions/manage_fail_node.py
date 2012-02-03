# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.shell import try_run
from hydra_agent.plugins import AgentPlugin


def fail_node(args):
    # force a manual failover by failing a node
    try_run("sync; sync; init 0", shell = True)


class FailNodePlugin(AgentPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("fail-node",
                              help="fail (i.e. shut down) this node")
        p.set_defaults(func=fail_node)
