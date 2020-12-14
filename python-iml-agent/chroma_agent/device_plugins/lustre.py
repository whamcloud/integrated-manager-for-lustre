# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import namedtuple
from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import daemon_log
from chroma_agent.log import console_log
from chroma_agent import version as agent_version
from chroma_agent.plugin_manager import DevicePlugin
from chroma_agent import plugin_manager
from chroma_agent.device_plugins.linux import LinuxDevicePlugin
from iml_common.lib.date_time import IMLDateTime

# FIXME: weird naming, 'LocalAudit' is the class that fetches stats
from chroma_agent.device_plugins.audit import local


VersionInfo = namedtuple("VersionInfo", ["epoch", "version", "release", "arch"])


class LustrePlugin(DevicePlugin):
    delta_fields = ["capabilities", "properties"]

    def __init__(self, session):
        self.reset_state()
        super(LustrePlugin, self).__init__(session)

    def reset_state(self):
        pass

    def _scan(self, initial=False):
        started_at = IMLDateTime.utcnow().isoformat()
        audit = local.LocalAudit()

        # FIXME: HYD-1095 we should be sending a delta instead of a full dump every time
        # FIXME: At this time the 'capabilities' attribute is unused on the manager
        return {
            "started_at": started_at,
            "agent_version": agent_version(),
            "capabilities": plugin_manager.ActionPluginManager().capabilities,
            "metrics": audit.metrics(),
            "properties": audit.properties(),
        }

    def start_session(self):
        self.reset_state()
        self._reset_delta()
        return self._delta_result(self._scan(initial=True), self.delta_fields)

    def update_session(self):
        return self._delta_result(self._scan(), self.delta_fields)
