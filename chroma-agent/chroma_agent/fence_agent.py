#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.shell import try_run, run


class FenceAgent(object):
    # subclasses can redefine _fence_state to change it's default fence mode
    _fence_state = "reboot"

    def __init__(self, node, fence_state = None):
        self.node = node
        if fence_state:
            self._fence_state = fence_state

    def initialize(self):
        pass

    def set_power_state(self, state):
        raise NotImplementedError()

    def fence(self):
        self.set_power_state(self._fence_state)

    def plug_status():
        raise NotImplementedError()

    def __getattr__(self, name):
        rc, stdout, stderr = run(["crm", "node", "attribute", self.node,
                                  "show", "fence_%s" % name])
        if rc == 0:
            value = stdout[stdout.rfind('=') + 1:]
        else:
            raise AttributeError("No such attribute %s" % name)

        return value.rstrip()


class fence_xvm(FenceAgent):
    def set_power_state(self, state):
        try_run(["fence_xvm", "-o", state, "-H", self.node])

    def plug_status(self):
        rc, stdout, stderr = run(["fence_xvm", "-o", "status", "-H", self.node])
        if rc == 0:
            return "on"
        else:
            return "off"

    def initialize(self):
        # install a firewall rule for this port
        #try_run(['/usr/sbin/lokkit', '-p', '1229:tcp'])
        pass


class fence_apc(FenceAgent):
    def set_power_state(self, state):
        try_run(["fence_apc", "-o", state, "-a", self.ipaddress,
                 "-l", self.login, "-p", self.password, "-n", self.plug])

    def plug_status(self):
        # just a guess at what this is going to look like for fence_apc
        # - don't have one to actually test for
        rc, stdout, stderr = run(["fence_apc", "-o", "status", "-a",
                                 self.ipaddress, "-l", self.login, "-p",
                                 self.password, "-n", self.plug])
        if rc == 0:
            return "on"
        else:
            return "off"
