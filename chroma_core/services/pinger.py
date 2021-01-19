# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


"""
Dev/test benchmarking tool for the RPC subsystem.
"""

import time

from chroma_core.services import ChromaService
from chroma_core.services.rpc import ServiceRpcInterface


class PingServer(object):
    def ping(self, data):
        return data

    def wait(self, data):
        time.sleep(5)
        return data


class PingServerRpcInterface(ServiceRpcInterface):
    methods = ["ping", "wait"]


class Service(ChromaService):
    def run(self):
        super(Service, self).run()

        self.server = PingServerRpcInterface(PingServer())
        self.server.run()

    def stop(self):
        super(Service, self).stop()

        self.server.stop()
