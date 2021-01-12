# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_agent import config
from chroma_agent.log import console_log
from chroma_agent.plugin_manager import DevicePluginManager
from chroma_agent.lib.agent_startup_functions import agent_daemon_startup_function
from chroma_agent.lib.agent_teardown_functions import agent_daemon_teardown_function
from emf_common.lib import util
from emf_common.lib.agent_rpc import agent_error, agent_result_ok
from emf_common.blockdevices.blockdevice import BlockDevice


def device_plugin(plugin=None):
    """
    Invoke a device plugin once to obtain a snapshot of what it
    is monitoring

    :param plugin: Plugin module name, or None for all plugins
    :return: dict of plugin name to data object
    """
    all_plugins = DevicePluginManager.get_plugins()
    if plugin is None:
        plugins = all_plugins
    elif plugin == "":
        plugins = {}
    else:
        plugins = {plugin: all_plugins[plugin]}

    result = {}
    for plugin_name, plugin_class in plugins.items():
        result[plugin_name] = plugin_class(None).start_session()

    return result


def trigger_plugin_update(agent_daemon_context, plugin_names):
    """
    Cause a device plugin to update on its next poll cycle irrespective of whether anything has changed or not.

    Because this function requires agent_daemon_context it is not available from the cli.

    :param agent_daemon_context: the context for the running agent daemon - None if the agent is not a daemon
    :param plugin_names: The plugins to force the update for, [] means all
    :return: result_agent_ok always
    """

    if plugin_names == []:
        plugin_names = agent_daemon_context.plugin_sessions.keys()

    for plugin_name in plugin_names:
        agent_daemon_context.plugin_sessions[plugin_name]._plugin.trigger_plugin_update = True


@agent_daemon_startup_function()
def initialise_block_device_drivers():
    """
    When the agent is run we want to allow block devices to do any initialization that they might need, this function
    may also be called by the manager.
    """
    console_log.info("Initialising drivers for block device types")
    for cls in util.all_subclasses(BlockDevice):
        error = cls.initialise_driver(config.profile_managed)

        if error:
            return agent_error(error)

    return agent_result_ok


@agent_daemon_teardown_function()
def terminate_block_device_drivers():
    """
    When the agent is stopped we want to allow block devices to do any termination that they might need, this function
    may also be called by the manager.
    """
    console_log.info("Terminating drivers for block device types")
    for cls in util.all_subclasses(BlockDevice):
        error = cls.terminate_driver()

        if error:
            return agent_error(error)

    return agent_result_ok


ACTIONS = [
    device_plugin,
    trigger_plugin_update,
    initialise_block_device_drivers,
    terminate_block_device_drivers,
]
CAPABILITIES = []
