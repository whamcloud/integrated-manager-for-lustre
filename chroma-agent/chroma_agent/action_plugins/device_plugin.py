#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


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

ACTIONS = [device_plugin]
CAPABILITIES = []
