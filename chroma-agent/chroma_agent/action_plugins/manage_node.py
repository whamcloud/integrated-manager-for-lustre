#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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


import os

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import console_log
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from chroma_agent.lib.pacemaker import PacemakerConfig
from chroma_agent.chroma_common.blockdevices.blockdevice import BlockDevice
from chroma_agent.chroma_common.lib import util
from chroma_agent.chroma_common.lib.agent_rpc import agent_error
from chroma_agent.chroma_common.lib.agent_rpc import agent_result_ok


def ssi(runlevel):
    # force a manual failover by failing a node
    AgentShell.try_run(["sync"])
    AgentShell.try_run(["sync"])
    AgentShell.try_run(["init", runlevel])


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
        AgentShell.try_run(["shutdown", "-H" if halt else "-h", at_time])

        console_log.info("Terminating")
        os._exit(0)

    raise CallbackAfterResponse(None, _shutdown)


def reboot_server(at_time = "now"):
    def _reboot():
        console_log.info("Initiating server reboot per manager request")
        # reboot(8) just calls shutdown anyhow.
        AgentShell.try_run(["shutdown", "-r", at_time])

        console_log.info("Terminating")
        os._exit(0)

    raise CallbackAfterResponse(None, _reboot)


def initialise_block_device_drivers():
    console_log.info("Initialising drivers for block device types")
    for cls in util.all_subclasses(BlockDevice):
        error = cls.initialise_driver()

        if error:
            return agent_error(error)

    return agent_result_ok

ACTIONS = [reboot_server, shutdown_server, fail_node, stonith, initialise_block_device_drivers]
