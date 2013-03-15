#!/usr/bin/python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import sys
import chroma_agent.fence_agent
from chroma_agent.shell import try_run, run


# flag to set whether we want to list a node that is off
print_if_plug_off = False


def print_node_status(node, fence_agent):
    plug_status = "off"
    agent = getattr(chroma_agent.fence_agent, fence_agent)
    plug_status = agent(node).plug_status()
    if plug_status == "on" or (print_if_plug_off and plug_status == "off"):
        print "%s junk %s" % (node, plug_status)


def main():
    nodename = ""
    for line in sys.stdin.readlines():
        line = line.strip()
        (name, value) = line.split("=", 1)
        if name == "option":
            option = value
        elif name == "nodename":
            nodename = value

    if option == "metadata":
        print """
<?xml version="1.0" ?>
<resource-agent name="fence_chroma" shortdesc="Fence agent for Intel Manager for Lustre Storage Servers">
<longdesc>fence_chroma is an I/O Fencing agent which can be used with Intel Manager for Lustre Storage Servers.</longdesc>
<parameters>
    <parameter name="port">
        <getopt mixed="-H" />
        <content type="string" />
        <shortdesc lang="en">Storage Server (machine name) to fence</shortdesc>
    </parameter>
    <parameter name="action">
        <getopt mixed="-o" />
        <content type="string" default="reboot" />
        <shortdesc lang="en">Fencing action ([reboot], metadata, list)</shortdesc>
    </parameter>
</parameters>
<actions>
    <action name="reboot" />
    <action name="metadata" />
    <action name="list" />
</actions>
</resource-agent>
"""
    elif option == "reboot":
        try_run(['chroma-agent', 'stonith', '--node', nodename])
    elif option == "list":
        rc, stdout, stderr = run(["crm", "node", "list"])
        node = None
        fence_agent = None
        for line in stdout.split('\n'):
            if line:
                if line[0] != '\t':
                    if node:
                        print_node_status(node, fence_agent)
                    node, status = line.split(": ")
                else:
                    attribute, value = line.lstrip().split(": ")
                    if attribute == "fence_agent":
                        fence_agent = value
        print_node_status(node, fence_agent)
