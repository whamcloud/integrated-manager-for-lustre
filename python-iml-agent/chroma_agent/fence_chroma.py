# -*- coding: utf-8 -*-
#!/usr/bin/env python
# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from chroma_agent.cli import configure_logging
from chroma_agent.action_plugins import manage_node
from chroma_agent.lib.pacemaker import PacemakerConfig
import socket


def stdin_to_args(stdin_lines=None):
    if not stdin_lines:
        stdin_lines = [line.strip() for line in sys.stdin.readlines()]

    args = []
    for line in stdin_lines:
        try:
            arg, value = line.split("=")
        except ValueError:
            raise RuntimeError("Bad input line: %s" % line)

        args.append("--%s" % arg)
        args.append(value)

    return args


def main(args=None):
    configure_logging()

    VALID_ACTIONS = ["off", "on", "reboot", "metadata", "list", "monitor"]

    epilog = """
With no command line argument, arguments are read from standard input.
Arguments read from standard input take the form of:

    arg1=value1
    arg2=value2

  action                Action to perform (%s)
  port                  Name of node on which to perform action
""" % ", ".join(
        VALID_ACTIONS
    )

    parser = ArgumentParser(
        description="Chroma Fence Agent",
        formatter_class=RawDescriptionHelpFormatter,
        epilog=epilog,
    )

    parser.add_argument("-o", "--option", "--action", dest="action", choices=VALID_ACTIONS)
    parser.add_argument(
        "-n",
        "--plug",
        "--nodename",
        "--port",
        dest="port",
        help="Name of node on which to perform action",
    )
    ns = parser.parse_args(args)

    if not ns.action and not ns.port:
        ns = parser.parse_args(stdin_to_args())

    if ns.action == "metadata":
        print(
            """<?xml version="1.0" ?>
<resource-agent name="fence_chroma" shortdesc="Fence agent for Integrated Manager for Lustre software Storage Servers">
<longdesc>fence_chroma is an I/O Fencing agent which can be used with Integrated Manager for Lustre software Storage Servers.</longdesc>
<vendor-url>http://www.whamcloud.com</vendor-url>
<parameters>
    <parameter name="port">
        <getopt mixed="-p" />
        <content type="string" />
        <shortdesc lang="en">Storage Server (machine name) to fence</shortdesc>
    </parameter>
    <parameter name="action">
        <getopt mixed="-o" />
        <content type="string" />
        <shortdesc lang="en">Fencing action (%s)</shortdesc>
    </parameter>
</parameters>
<actions>
    <action name="reboot" />
    <action name="off" />
    <action name="on" />
    <action name="metadata" />
    <action name="list" />
    <action name="monitor" />
</actions>
</resource-agent>
"""
            % ", ".join(VALID_ACTIONS)
        )
    elif ns.action in ["on", "off"]:
        node = PacemakerConfig().get_node(ns.port)
        getattr(node, "fence_%s" % ns.action)()
    elif ns.action == "reboot":
        manage_node.stonith(ns.port)
    elif ns.action == "list":
        for node in PacemakerConfig().fenceable_nodes:
            print("%s," % node.name)
    elif ns.action == "monitor":
        rc = PacemakerConfig().get_node(ns.port or socket.gethostname()).fence_monitor()
        sys.exit(rc)
    else:
        # Supposedly impossible to get here with argparse, but one never
        # knows...
        raise RuntimeError("Invalid action: %s" % ns.action)
