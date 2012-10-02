#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import datetime
import os
import socket

from chroma_agent.plugins import ActionPlugin
from chroma_agent.utils import list_capabilities
from chroma_agent import version


def _selinux_enabled():
    """Returns true if SELinux is enabled."""
    from chroma_agent.shell import run
    return run("/usr/sbin/selinuxenabled")[0] == 0


def host_properties(args = None):
    return {
        'time': datetime.datetime.utcnow().isoformat() + "Z",
        'nodename': os.uname()[1],
        'fqdn': socket.getfqdn(),
        'capabilities': list_capabilities(),
        'agent_version': version(),
        'selinux_enabled': _selinux_enabled()
    }


class HostScanPlugin(ActionPlugin):
    def register_commands(self, parser):
        p = parser.add_parser("host-properties")
        p.set_defaults(func=host_properties)
