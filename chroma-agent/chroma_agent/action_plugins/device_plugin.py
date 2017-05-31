# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_agent.plugin_manager import DevicePluginManager


def device_plugin(plugin = None):
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


ACTIONS = [device_plugin, trigger_plugin_update]
CAPABILITIES = []
