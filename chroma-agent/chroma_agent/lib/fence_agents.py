#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent import shell

# TODO: Refactor out this hard-coded stuff in favor of using templates
# supplied by the manager.


class FenceAgent(object):
    def toggle_outlet(self, state):
        shell.try_run(self.base_cmd + ['-n', self.plug, '-o', state])

    def list(self):
        shell.try_run(self.base_cmd + ['-a', 'list'])

    def status(self):
        shell.try_run(self.base_cmd + ['-n', self.plug, '-o', 'status'])

    def off(self):
        self.toggle_outlet('off')

    def on(self):
        self.toggle_outlet('on')

    def reboot(self):
        self.toggle_outlet('reboot')


class fence_apc(FenceAgent):
    def __init__(self, agent, login, password, ipaddr, plug, ipport=23):
        self.plug = plug
        self.base_cmd = [agent, '-a', ipaddr, '-u', str(ipport), '-l', login, '-p', password]


class fence_virsh(FenceAgent):
    def __init__(self, agent, login, plug, ipaddr, ipport=22, password=None, identity_file=None):
        self.plug = plug
        if password:
            auth = ['-p', password]
        elif identity_file:
            auth = ['-k', identity_file]
        else:
            raise RuntimeError("Neither password nor identity_file were supplied")
        self.base_cmd = [agent, '-a', ipaddr, '-u', str(ipport), '-l', login, '-x'] + auth
