# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.plugins import DevicePluginManager, ActionPlugin


class DevicePluginAction(ActionPlugin):
    def device_plugin(self, args):
        all_plugins = DevicePluginManager.get_plugins()
        if args.plugin == None:
            plugins = all_plugins
        elif args.plugin == "":
            plugins = {}
        else:
            plugins = {args.plugin: all_plugins[args.plugin]}

        result = {}
        for plugin_name, plugin_class in plugins.items():
            result[plugin_name] = plugin_class().start_session()

        return result

    def register_commands(self, parser):
        p = parser.add_parser("device-plugin",
                              help="get one or more device plugins' reports")
        p.add_argument('--plugin', required = False)
        p.set_defaults(func=self.device_plugin)
