#!/usr/bin/python
#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import sys
import chroma_agent.fence_agent
from chroma_agent.shell import try_run, run
import io
import os


# flag to set whether we want to list a node that is off
print_if_plug_off = False


def print_node_status(node, fence_agent):
    plug_status = "off"
    agent = getattr(chroma_agent.fence_agent, fence_agent)
    plug_status = agent(node).plug_status()
    if plug_status == "on" or (print_if_plug_off and plug_status == "off"):
        print "%s junk %s" % (node, plug_status)


def main():
    dbg = io.open("/tmp/fence_chroma_debug.%s" % os.getpid(), "w")
    nodename = ""
    for line in sys.stdin.readlines():
        dbg.writelines(u"<: %s" % line)
        line = line.strip()
        (name, value) = line.split("=", 1)
        if name == "action":
            action = value
        elif name == "nodename":
            nodename = value

    if action == "metadata":
        print """<?xml version="1.0" ?>
<resource-agent name="fence_chroma" shortdesc="Fence agent for Intel Manager for Lustre Storage Servers">
<longdesc>fence_chroma is an I/O Fencing agent which can be used with Intel Manager for Lustre Storage Servers.</longdesc>
<vendor-url>http://www.intel.com</vendor-url>
<parameters>
    <parameter name="action" unique="0" required="1">
        <getopt mixed="-o, --action=&lt;action&gt;" />
        <content type="string" default="reboot" />
        <shortdesc lang="en">Fencing action ([reboot], metadata, list)</shortdesc>
    </parameter>
    <parameter name="port" unique="0" required="1">
        <getopt mixed="-H, --plug=&lt;id&gt;" />
        <content type="string" />
        <shortdesc lang="en">Storage Server (machine name) to fence</shortdesc>
    </parameter>
</parameters>
<actions>
    <action name="on" />
    <action name="off" />
    <action name="reboot" />
    <action name="status" />
    <action name="list" />
    <action name="monitor" />
    <action name="metadata" />
</actions>
</resource-agent>"""
    elif action == "reboot":
        try_run(['chroma-agent', 'stonith', '--node', nodename])
    elif action == "list":
        rc, stdout, stderr = run(["crm_node", "-l"])
        node = None
        fence_agent = None
        for line in stdout.split('\n'):
            if line:
                node = line.split()[1]
                if node:
                    rc, stdout, stderr = run(["crm_attribute", "--type", "nodes",
                                              "--node-uname", node, "--attr-name",
                                              "fence_agent", "--get-value"])
                    fence_agent = stdout.split()[2].split('=')[1]
                    print_node_status(node, fence_agent)

    dbg.close()
