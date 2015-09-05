#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
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


"""
Actions for registration and deregistration of a server (adding and removing
it from chroma manager)
"""

import os

from chroma_agent import config
from chroma_agent.agent_client import AgentClient, HttpError
from chroma_agent.agent_daemon import ServerProperties
from chroma_agent.lib.shell import AgentShell
from chroma_agent.crypto import Crypto
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from chroma_agent.log import console_log
from chroma_agent.plugin_manager import ActionPluginManager, DevicePluginManager


def _service_is_running():
    return AgentShell.run(["/sbin/service", "chroma-agent", "status"])[0] == 0


def _start_service():
    AgentShell.try_run(["/sbin/service", "chroma-agent", "start"])


def _service_is_enabled():
    return AgentShell.run(["/sbin/chkconfig", "chroma-agent"])[0] == 0


def _enable_service():
    AgentShell.try_run(["/sbin/chkconfig", "chroma-agent", "on"])


def _disable_service():
    AgentShell.try_run(["/sbin/chkconfig", "chroma-agent", "off"])


def deregister_server():
    config.delete('settings', 'server')

    def disable_and_kill():
        console_log.info("Disabling chroma-agent service")
        _disable_service()

        console_log.info("Terminating")
        os._exit(0)

    raise CallbackAfterResponse(None, disable_and_kill)


def register_server(url, ca, secret, address = None):

    if _service_is_running():
        console_log.warning("chroma-agent service was running before registration, stopping.")
        AgentShell.try_run(["/sbin/service", "chroma-agent", "stop"])

    crypto = Crypto(config.path)
    # Call delete in case we are over-writing a previous configuration that wasn't removed properly
    crypto.delete()
    crypto.install_authority(ca)

    agent_client = AgentClient(url + "register/%s/" % secret,
        ActionPluginManager(),
        DevicePluginManager(),
        ServerProperties(),
        crypto)

    registration_result = agent_client.register(address)
    crypto.install_certificate(registration_result['certificate'])

    config.set('settings', 'server', {'url': url})

    console_log.info("Enabling chroma-agent service")
    AgentShell.try_run(["/sbin/chkconfig", "chroma-agent", "on"])

    console_log.info("Starting chroma-agent service")
    AgentShell.try_run(["/sbin/service", "chroma-agent", "start"])

    return registration_result


def reregister_server(url, address):
    "Update manager url and register agent address with manager."
    if _service_is_running():
        console_log.warning("chroma-agent service was running before registration, stopping.")
        AgentShell.try_run(["/sbin/service", "chroma-agent", "stop"])

    config.set('settings', 'server', {'url': url})
    crypto = Crypto(config.path)
    agent_client = AgentClient(url + 'reregister/', ActionPluginManager(), DevicePluginManager(), ServerProperties(), crypto)
    data = {'address': address, 'fqdn': agent_client._fqdn}

    try:
        result = agent_client.post(data)
    except HttpError:
        console_log.error("Reregistration failed to %s with request %s" % (agent_client.url, data))
        raise

    console_log.info("Starting chroma-agent service")
    AgentShell.try_run(["/sbin/service", "chroma-agent", "start"])

    return result


def test():
    """A dummy action used for testing that the agent is available
    and successfully running actions."""
    pass

ACTIONS = [deregister_server, register_server, reregister_server, test]
CAPABILITIES = []
