#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime
import os
import socket

from chroma_agent.plugins import ActionPlugin


def get_fqdn(args = None):
    return socket.getfqdn()


def get_nodename(args = None):
    return os.uname()[1]


def get_time(args = None):
    return datetime.datetime.utcnow().isoformat() + "Z"


class HostScanPlugin(ActionPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("get-fqdn",
                              help="get the host's FQDN")
        p.set_defaults(func=get_fqdn)

        p = parser.add_parser("get-nodename",
                              help="get the host's nodename")
        p.set_defaults(func=get_nodename)

        p = parser.add_parser("get-time")
        p.set_defaults(func=get_time)
