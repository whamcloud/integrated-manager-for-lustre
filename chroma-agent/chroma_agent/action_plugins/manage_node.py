#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import os
from chroma_agent import shell
from chroma_agent.log import console_log
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from chroma_agent.lib.pacemaker import PacemakerConfig


def ssi(runlevel):
    # force a manual failover by failing a node
    shell.try_run(["sync"])
    shell.try_run(["sync"])
    shell.try_run(["init", runlevel])


def fail_node():
    ssi("0")


def stonith(node):
    p_cfg = PacemakerConfig()

    # TODO: signal that manager that a STONITH has been done so that it
    #       doesn't treat it as an AWOL
    console_log.info("Rebooting %s per a STONITH request" % node)

    p_cfg.get_node(node).fence_reboot()


def shutdown_server(halt = True, at_time = "now"):
    def _shutdown():
        console_log.info("Initiating server shutdown per manager request")
        # This will initiate a "nice" shutdown with a wall from root, etc.
        shell.try_run(["shutdown", "-H" if halt else "-h", at_time])

        console_log.info("Terminating")
        os._exit(0)

    raise CallbackAfterResponse(None, _shutdown)


def reboot_server(at_time = "now"):
    def _reboot():
        console_log.info("Initiating server reboot per manager request")
        # reboot(8) just calls shutdown anyhow.
        shell.try_run(["shutdown", "-r", at_time])

        console_log.info("Terminating")
        os._exit(0)

    raise CallbackAfterResponse(None, _reboot)


ACTIONS = [reboot_server, shutdown_server, fail_node, stonith]
