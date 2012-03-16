# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.plugins import ActionPlugin
from os import uname


def get_fqdn(args = None):
    from socket import getfqdn
    return getfqdn()


def get_nodename(args = None):
    return uname()[1]


class HostScanPlugin(ActionPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("get-fqdn",
                              help="get the host's FQDN")
        p.set_defaults(func=get_fqdn)

        p = parser.add_parser("get-nodename",
                              help="get the host's nodename")
        p.set_defaults(func=get_nodename)
