#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os
import chroma_agent.fence_agent
from chroma_agent.shell import try_run, run
from chroma_agent.log import console_log
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse


def _power(node, state):
    valid_states = ["on", "off", "reboot"]
    if state not in valid_states:
        raise RuntimeError("state must be one of %s" % ", ".join(valid_states))

    rc, stdout, stderr = run(["crm_attribute", "--type", "nodes",
                              "--node-uname", node, "--attr-name",
                              "fence_agent", "--get-value"])
    fence_agent = stdout.split()[2].split('=')[1]

    agent = getattr(chroma_agent.fence_agent, fence_agent)

    agent(node).set_power_state(state)


def ssi(runlevel):
    # force a manual failover by failing a node
    try_run(["sync"])
    try_run(["sync"])
    try_run(["init", runlevel])


def fail_node():
    ssi("0")


def stonith(node):

    # TODO: signal that manager that a STONITH has been done so that it
    #       doesn't treat it as an AWOL
    console_log.info("Rebooting per a STONITH request")

    rc, stdout, stderr = run(["crm_attribute", "--type", "nodes",
                              "--node-uname", node, "--attr-name",
                              "fence_agent", "--get-value"])
    fence_agent = stdout.split()[2].split('=')[1]

    agent = getattr(chroma_agent.fence_agent, fence_agent)

    agent(node).fence()


def shutdown_server(halt = True, at_time = "now"):
    def _shutdown():
        from chroma_agent.shell import try_run
        console_log.info("Initiating server shutdown per manager request")
        # This will initiate a "nice" shutdown with a wall from root, etc.
        try_run(["shutdown", "-H" if halt else "-h", at_time])

        console_log.info("Terminating")
        os._exit(0)

    raise CallbackAfterResponse(None, _shutdown)


def reboot_server(at_time = "now"):
    def _reboot():
        from chroma_agent.shell import try_run
        console_log.info("Initiating server reboot per manager request")
        # reboot(8) just calls shutdown anyhow.
        try_run(["shutdown", "-r", at_time])

        console_log.info("Terminating")
        os._exit(0)

    raise CallbackAfterResponse(None, _reboot)


ACTIONS = [reboot_server, shutdown_server, fail_node, stonith]
