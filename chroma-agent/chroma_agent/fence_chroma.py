#!/usr/bin/env python
#
# INTEL CONFIDENTIAL
#
# Copyright 2013 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from chroma_agent.action_plugins import manage_node
from chroma_agent.lib.pacemaker import PacemakerConfig


p_cfg = PacemakerConfig()


def list_fenceable_nodes():
    for node in p_cfg.fenceable_nodes:
        print "%s," % node.name


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
    epilog = """
With no command line argument, arguments are read from standard input.
Arguments read from standard input take the form of:

    arg1=value1
    arg2=value2

  option                Action to perform (off, on, reboot, metadata, monitor, list)
  nodename              Name of node on which to perform action
  port                  Optional port parameter, aliases to nodename
"""

    parser = ArgumentParser(description="Chroma Fence Agent",
                            formatter_class=RawDescriptionHelpFormatter,
                            epilog=epilog)

    parser.add_argument("-o", "--option", choices=["off", "on", "reboot", "metadata", "list", "monitor"])
    parser.add_argument("-H", "--nodename", help="Name of node on which to perform action")
    parser.add_argument("-n", "--port", help="Optional port parameter, aliases to nodename")
    ns = parser.parse_args(args)

    if not ns.option and not ns.nodename:
        ns = parser.parse_args(stdin_to_args())

    # This all bears some explanation. When pacemaker invokes stonith, it
    # sends parameters via stdin rather than via command-line options. It
    # always sends nodename, hence the preference for its use.
    if ns.nodename and ns.port and not ns.nodename == ns.port:
        sys.stderr.write("Both nodename and port were supplied, but do not match!\n")
        sys.exit(1)
    elif ns.port and not ns.nodename:
        ns.nodename = ns.port

    if ns.option == "metadata":
        print """
<?xml version="1.0" ?>
<resource-agent name="fence_chroma" shortdesc="Fence agent for Intel Manager for Lustre Storage Servers">
<longdesc>fence_chroma is an I/O Fencing agent which can be used with Intel Manager for Lustre Storage Servers.</longdesc>
<parameters>
    <parameter name="nodename">
        <getopt mixed="-H" />
        <content type="string" />
        <shortdesc lang="en">Storage Server (machine name) to fence</shortdesc>
    </parameter>
    <parameter name="option">
        <getopt mixed="-o" />
        <content type="string" default="reboot" />
        <shortdesc lang="en">Fencing action ([reboot], metadata, list)</shortdesc>
    </parameter>
</parameters>
<actions>
    <action name="reboot" />
    <action name="metadata" />
    <action name="list" />
    <action name="monitor" />
</actions>
</resource-agent>
"""
    elif ns.option in ["on", "off"]:
        node = p_cfg.get_node(ns.nodename)
        getattr(node, "fence_%s" % ns.option)()
    elif ns.option == "reboot":
        manage_node.stonith(ns.nodename)
    elif ns.option == "monitor":
        # TODO: What does "monitor" mean for this agent? We have to have it
        # to keep pacemaker happy, but longer-term it might make sense to
        # make this a meta-monitor, in that it invokes the monitor option for
        # all sub-agents and aggregates the results.
        sys.exit(0)
    elif ns.option == "list":
        list_fenceable_nodes()
