# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
Actions for registration and deregistration of a server (adding and removing
it from manager)
"""

from chroma_agent import conf
from chroma_agent.agent_client import AgentClient, HttpError
from chroma_agent.agent_daemon import ServerProperties
from chroma_agent.crypto import Crypto
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from chroma_agent.log import console_log
from chroma_agent.plugin_manager import ActionPluginManager, DevicePluginManager
from iml_common.lib.service_control import ServiceControl
from iml_common.lib.agent_rpc import agent_ok_or_error

agent_service = ServiceControl.create("chroma-agent")


def _service_is_running():
    # returns True if running
    return agent_service.running


def deregister_server():
    conf.remove_server_url()

    def disable_and_kill():
        console_log.info("Terminating")

        storage_server_target = ServiceControl.create("iml-storage-server.target")
        storage_server_target.disable()
        storage_server_target.stop()

    raise CallbackAfterResponse(None, disable_and_kill)


def register_server(url, ca, secret, address=None):
    if _service_is_running() is True:
        console_log.warning("chroma-agent service was running before registration, stopping.")
        agent_service.stop()

    crypto = Crypto(conf.ENV_PATH)
    # Call delete in case we are over-writing a previous configuration that wasn't removed properly
    crypto.delete()
    crypto.install_authority(ca)

    agent_client = AgentClient(
        url + "register/%s/" % secret,
        ActionPluginManager(),
        DevicePluginManager(),
        ServerProperties(),
        crypto,
    )

    registration_result = agent_client.register(address)
    crypto.install_certificate(registration_result["certificate"])

    conf.set_server_url(url)

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

    conf.set_server_url(url)
    crypto = Crypto(conf.ENV_PATH)
    agent_client = AgentClient(
        url + "reregister/",
        ActionPluginManager(),
        DevicePluginManager(),
        ServerProperties(),
        crypto,
    )
    data = {"address": address, "fqdn": agent_client._fqdn}

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
