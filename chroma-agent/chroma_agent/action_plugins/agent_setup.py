# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
Actions for registration and deregistration of a server (adding and removing
it from manager)
"""

import os

from chroma_agent import config
from chroma_agent.agent_client import AgentClient, HttpError
from chroma_agent.agent_daemon import ServerProperties
from chroma_agent.crypto import Crypto
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from chroma_agent.log import console_log
from chroma_agent.plugin_manager import ActionPluginManager, DevicePluginManager
from iml_common.lib.service_control import ServiceControl
from iml_common.lib.agent_rpc import agent_ok_or_error


agent_service = ServiceControl.create('chroma-agent')


def _service_is_running():
    # returns True if running
    return agent_service.running


def _start_service():
    return agent_ok_or_error(agent_service.start())


def _stop_service():
    return agent_ok_or_error(agent_service.stop())


def _service_is_enabled():
    return agent_service.enabled


def _enable_service():
    return agent_ok_or_error(agent_service.enable())


def _disable_service():
    return agent_ok_or_error(agent_service.disable())


def deregister_server():
    config.delete('settings', 'server')

    def disable_and_kill():
        console_log.info("Disabling chroma-agent service")
        _disable_service()

        console_log.info("Terminating")
        os._exit(0)

    raise CallbackAfterResponse(None, disable_and_kill)


def register_server(url, ca, secret, address =None):
    if _service_is_running() is True:
        console_log.warning("chroma-agent service was running before registration, stopping.")
        agent_service.stop()

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
    agent_service.enable()

    console_log.info("Starting chroma-agent service")
    agent_service.start()

    return registration_result


def reregister_server(url, address):
    """ Update manager url and register agent address with manager """
    if _service_is_running() is True:
        console_log.warning("chroma-agent service was running before registration, stopping.")
        agent_service.stop()

    config.set('settings', 'server', {'url': url})
    crypto = Crypto(config.path)
    agent_client = AgentClient(url + 'reregister/', ActionPluginManager(), DevicePluginManager(), ServerProperties(),
                               crypto)
    data = {'address': address, 'fqdn': agent_client._fqdn}

    try:
        result = agent_client.post(data)
    except HttpError:
        console_log.error("Reregistration failed to %s with request %s" % (agent_client.url, data))
        raise

    console_log.info("Starting chroma-agent service")
    agent_service.start()

    return result


def test():
    """A dummy action used for testing that the agent is available
    and successfully running actions."""
    pass

ACTIONS = [deregister_server, register_server, reregister_server, test]
CAPABILITIES = []
