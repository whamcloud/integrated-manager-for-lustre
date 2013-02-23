#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import socket
import chroma_agent.fence_agent
from chroma_agent.shell import try_run
from chroma_agent.log import console_log


def _power(node, state):
    valid_states = ["on", "off", "reboot"]
    if state not in valid_states:
        raise RuntimeError("state must be one of %s" % ", ".join(valid_states))

    agent = getattr(chroma_agent.fence_agent,
                    chroma_agent.fence_agent.get_attribute("agent",
                                                           socket.gethostname()))
    agent(node).set_power_state(state)


def ssi(runlevel):
    # force a manual failover by failing a node
    try_run(["sync"])
    try_run(["sync"])
    try_run(["init", runlevel])


def shutdown():
    ssi("0")


def fail_node():
    shutdown()


def stonith(node):

    # TODO: signal that manager that a STONITH has been done so that it
    #       doesn't treat it as an AWOL
    console_log.info("Rebooting per a STONITH request")

    agent = getattr(chroma_agent.fence_agent,
                    chroma_agent.fence_agent.FenceAgent(node).agent)

    agent(node).fence()


ACTIONS = [fail_node, stonith]
