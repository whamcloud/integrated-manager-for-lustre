#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2015 Intel Corporation All Rights Reserved.
#
# The source code contained or described herein and all documents related
# to the source code ("Material") are owned by Intel Corporation or its
# suppliers or licensors. Title to the Material remains with Intel Corporation
# or its suppliers and licensors. The Material contains trade secrets and
# proprietary and confidential information of Intel or its suppliers and
# licensors. The Material is protected by worldwide copyright and trade secret
# laws and treaty provisions. No part of the Material may be used, copied,
# reproduced, modified, published, uploaded, posted, transmitted, distributed,
# or disclosed in any way without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be
# express and approved by Intel in writing.


from time import sleep
from threading import Thread

from os.path import isfile, expanduser

# TODO: Refactor out this hard-coded stuff in favor of using templates
# supplied by the manager.
from chroma_agent.chroma_common.lib import shell


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


class fence_apc_snmp(FenceAgent):
    def __init__(self, agent, login, password, ipaddr, plug, ipport=161):
        self.plug = plug
        self.base_cmd = [agent, '-a', ipaddr, '-u', str(ipport), '-l', login, '-p', password]


class fence_virsh(FenceAgent):
    def __init__(self, agent, login, plug, ipaddr, ipport=22, password=None, identity_file="%s/.ssh/id_rsa" % expanduser("~")):
        self.plug = plug
        if identity_file and isfile(identity_file):
            auth = ['-k', identity_file]
        elif password:
            auth = ['-p', password]
        else:
            raise RuntimeError("Neither password nor identity_file were supplied")
        self.base_cmd = [agent, '-a', ipaddr, '-u', str(ipport), '-l', login, '-x'] + auth

    def on(self):
        """Override super.on to wait 15 seconds then process as usual.

        Real servers start slower then virtual ones do.  This simulates the production
        environment more closely.  This was introduced to prevent HYD-2889 from occuring
        in the testing.
        """

        def delay_on():
            sleep(15)
            super(fence_virsh, self).on()

        Thread(target=delay_on).start()


class fence_ipmilan(FenceAgent):
    def __init__(self, agent, login, password, ipaddr, lanplus=False):
        if lanplus:
            self.base_cmd = [agent, '-P', '-a', ipaddr, '-l', login, '-p', password]
        else:
            self.base_cmd = [agent, '-a', ipaddr, '-l', login, '-p', password]

    def toggle_outlet(self, state):
        shell.try_run(self.base_cmd + ['-o', state])
