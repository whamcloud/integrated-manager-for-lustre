#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import threading
import logging

from chroma_agent.agent_daemon import daemon_log
from chroma_core.services import ChromaService
from chroma_core.services.cluster_sim.simulator import ClusterSimulator
from chroma_core.services.cluster_sim.simulator import log as simulator_log

import settings


class Service(ChromaService):
    def __init__(self):
        super(Service, self).__init__()
        self.stopping = threading.Event()

    def run(self):
        N = 1
        folder = 'cluster_sim'
        url = settings.SERVER_HTTP_URL

        simulator_log.addHandler(logging.StreamHandler())

        daemon_log.addHandler(logging.StreamHandler())
        daemon_log.setLevel(logging.DEBUG)
        handler = logging.FileHandler("chroma-agent.log")
        handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
        daemon_log.addHandler(handler)

        self.log.info("Running using config '%s' for %s hosts" % (folder, N))
        self.simulator = ClusterSimulator(N, folder, url)
        self.simulator.register_all()
        self.simulator.start_all()
        while not self.stopping.is_set():
            self.stopping.wait(timeout = 10)

    def stop(self):
        self.simulator.stop()
        self.stopping.set()
