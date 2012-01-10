# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.plugins import AgentPlugin


def get_fqdn(args = None):
    from socket import getfqdn
    return getfqdn()


class FqdnPlugin(AgentPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("get-fqdn",
                              help="get the host's FQDN")
        p.set_defaults(func=get_fqdn)
