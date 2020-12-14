# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from time import sleep
from threading import Thread

from os.path import isfile, expanduser

# TODO: Refactor out this hard-coded stuff in favor of using templates
# supplied by the manager.
from chroma_agent.lib.shell import AgentShell
from iml_common.lib.util import platform_info


class FenceAgent(object):
    def __init__(self, plug, base_cmd):
        self.plug = plug
        self.base_cmd = base_cmd

    def toggle_outlet(self, state):
        AgentShell.try_run(self.base_cmd + ["-n", self.plug, "-o", state])

    def list(self):
        if platform_info.distro_version >= 7.0:
            AgentShell.try_run(self.base_cmd + ["-n", self.plug, "-o", "list-status"])
        else:
            AgentShell.try_run(self.base_cmd + ["-a", "list"])

    def status(self):
        AgentShell.try_run(self.base_cmd + ["-n", self.plug, "-o", "status"])

    def monitor(self):
        result = AgentShell.run(self.base_cmd + ["-n", self.plug, "-o", "monitor"])
        return result.rc

    def off(self):
        self.toggle_outlet("off")

    def on(self):
        self.toggle_outlet("on")

    def reboot(self):
        self.toggle_outlet("reboot")


class fence_apc(FenceAgent):
    def __init__(self, agent, login, password, ipaddr, plug, ipport=23):
        super(fence_apc, self).__init__(plug, [agent, "-a", ipaddr, "-u", str(ipport), "-l", login, "-p", password])


class fence_apc_snmp(FenceAgent):
    def __init__(self, agent, login, password, ipaddr, plug, ipport=161):
        super(fence_apc_snmp, self).__init__(
            plug, [agent, "-a", ipaddr, "-u", str(ipport), "-l", login, "-p", password]
        )


class fence_virsh(FenceAgent):
    def __init__(
        self,
        agent,
        login,
        plug,
        ipaddr,
        ipport=22,
        password=None,
        identity_file="%s/.ssh/id_rsa" % expanduser("~"),
    ):
        if identity_file and isfile(identity_file):
            auth = ["-k", identity_file]
        elif password:
            auth = ["-p", password]
        else:
            raise RuntimeError("Neither password nor identity_file were supplied")

        super(fence_virsh, self).__init__(plug, [agent, "-a", ipaddr, "-u", str(ipport), "-l", login, "-x"] + auth)

    def on(self):
        """Override super.on to wait 15 seconds then process as usual.

        Real servers start slower then virtual ones do.  This simulates the production
        environment more closely.  This was introduced to prevent HYD-2889 from occurring
        in the testing.
        """

        def delay_on():
            sleep(15)
            super(fence_virsh, self).on()

        Thread(target=delay_on).start()


class fence_vbox(FenceAgent):
    def __init__(
        self,
        agent,
        login,
        plug,
        ipaddr,
        ipport=22,
        password=None,
        identity_file="%s/.ssh/id_rsa" % expanduser("~"),
    ):
        if password:
            auth = ["-p", password]
        elif identity_file and isfile(identity_file):
            auth = ["-k", identity_file]
        else:
            raise RuntimeError("Neither password nor identity_file were supplied")

        super(fence_vbox, self).__init__(plug, [agent, "-a", ipaddr, "-u", str(ipport), "-l", login, "-x"] + auth)

    def on(self):
        """Override super.on to wait 15 seconds then process as usual.

        Real servers start slower than virtual ones do.  This simulates the production
        environment more closely.  This was introduced to prevent HYD-2889 from occurring
        in the testing.
        """

        def delay_on():
            sleep(15)
            super(fence_vbox, self).on()

        Thread(target=delay_on).start()


class fence_ipmilan(FenceAgent):
    def __init__(self, agent, login, password, ipaddr, lanplus=False):
        if lanplus:
            base_cmd = [agent, "-P", "-a", ipaddr, "-l", login, "-p", password]
        else:
            base_cmd = [agent, "-a", ipaddr, "-l", login, "-p", password]

        super(fence_ipmilan, self).__init__("", base_cmd)

    def toggle_outlet(self, state):
        AgentShell.try_run(self.base_cmd + ["-o", state])
