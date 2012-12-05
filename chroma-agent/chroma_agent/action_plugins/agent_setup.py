#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
import time
from chroma_agent import shell
from chroma_agent.agent_client import AgentClient
from chroma_agent.agent_daemon import ServerProperties
from chroma_agent.crypto import Crypto
from chroma_agent.log import console_log
import os

from chroma_agent.plugin_manager import ActionPluginManager, DevicePluginManager


def _service_is_running():
    return shell.run(["/sbin/service", "chroma-agent", "status"])[0] == 0


def _start_service():
    shell.try_run(["/sbin/service", "chroma-agent", "start"])


def _service_is_enabled():
    return shell.run(["/sbin/chkconfig", "chroma-agent"])[0] == 0


def _enable_service():
    shell.try_run(["/sbin/chkconfig", "chroma-agent", "on"])


def _disable_service():
    shell.try_run(["/sbin/chkconfig", "chroma-agent", "off"])


def deregister_server():
    from chroma_agent.store import AgentStore
    AgentStore.remove_server_conf()

    console_log.info("Disabling chroma-agent service")
    _disable_service()

    console_log.info("Terminating")

    KILL_DELAY = 20

    # This is a little bit rude, but this is meant to be a very final shutdown
    # and it would be a hassle to call all the way back out to the main thread.
    # This should be at least fairly robust.  To make it a bit cleaner, one could either
    # provide a way for this acitonplugin to signal a quit to the class executing it, or
    # provide the deregistration as a special agent protocol operation that doesn't
    # make it down here into plugin territory.
    # The functional downside to this approach is that if the communications
    # are interrupted, we will kill ourselves without sending the completion to
    # the manager, and the user will have to 'force remove' this host.
    # FIXME: that's probably annoying enough to justify doing this in
    # a way that guarantees we won't kill ourselves before sending the response.
    class KillLater(threading.Thread):
        def run(self):
            time.sleep(KILL_DELAY)
            Crypto().delete()
            console_log.info("Terminating now")
            os._exit(0)

    # Delay the quit so that there is time to send the result of this operation
    # back to the manager.
    console_log.info("Terminating in %s seconds" % KILL_DELAY)
    KillLater().start()


def register_server(url, ca, address = None):
    from chroma_agent.store import AgentStore

    if _service_is_running():
        console_log.warning("chroma-agent service was running before registration, stopping.")
        shell.try_run(["/sbin/service", "chroma-agent", "stop"])

    crypto = Crypto()
    # Call delete in case we are over-writing a previous configuration that wasn't removed properly
    crypto.delete()
    crypto.install_authority(ca)

    agent_client = AgentClient(url + "register/xyz/",
        ActionPluginManager(),
        DevicePluginManager(),
        ServerProperties(),
        crypto)

    registration_result = agent_client.register(address)
    crypto.install_certificate(registration_result['certificate'])

    AgentStore.set_server_conf({'url': url})

    console_log.info("Enabling chroma-agent service")
    shell.try_run(["/sbin/chkconfig", "chroma-agent", "on"])

    console_log.info("Starting chroma-agent service")
    shell.try_run(["/sbin/service", "chroma-agent", "start"])

    return registration_result

ACTIONS = [deregister_server, register_server]
CAPABILITIES = []
