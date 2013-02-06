#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.shell import try_run


def fail_node(args):
    # force a manual failover by failing a node
    try_run(["sync"])
    try_run(["sync"])
    try_run(["init", "0"])

ACTIONS = [fail_node]
CAPABILITIES = []
