#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import argparse
import logging
import signal
import threading

from cluster_sim.log import log
from cluster_sim.simulator import ClusterSimulator

from chroma_agent.agent_daemon import daemon_log
daemon_log.addHandler(logging.StreamHandler())
daemon_log.setLevel(logging.DEBUG)
handler = logging.FileHandler("chroma-agent.log")
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%d/%b/%Y:%H:%M:%S'))
daemon_log.addHandler(handler)


class SimulatorCli(object):
    def __init__(self):
        self._stopping = threading.Event()

    def setup(self, args):
        log.info("Setting up simulator configuration for %s servers in %s/" % (args.server_count, args.config))

        server_count = int(args.server_count)
        if args.volume_count:
            volume_count = int(args.volume_count)
        else:
            volume_count = server_count * 2

        self.simulator = ClusterSimulator(args.config, args.url)
        self.simulator.setup(server_count, volume_count)
        self.stop()

    def register(self, args):
        self.simulator = ClusterSimulator(args.config, args.url)
        log.info("Registering %s servers in %s/" % (len(self.simulator.servers), args.config))
        self.simulator.register_all()

    def run(self, args):
        self.simulator = ClusterSimulator(args.config, args.url)
        log.info("Running %s servers in %s/" % (len(self.simulator.servers), args.config))
        self.simulator.start_all()

    def stop(self):
        self.simulator.stop()
        self._stopping.set()

    def main(self):
        log.addHandler(logging.StreamHandler())

        parser = argparse.ArgumentParser(description = "Cluster simulator")
        parser.add_argument('--config', required = False, help = "Simulator configuration/state directory", default = "cluster_sim")
        parser.add_argument('--url', required = False, help = "Chroma manager URL", default = "https://localhost:8000/")
        subparsers = parser.add_subparsers()
        setup_parser = subparsers.add_parser("setup")
        setup_parser.add_argument('--server_count', required = False, help = "Number of simulated storage servers", default = '8')
        setup_parser.add_argument('--volume_count', required = False, help = "Number of simulated storage devices, defaults to twice the number of servers")
        setup_parser.set_defaults(func = self.setup)

        register_parser = subparsers.add_parser("register")
        register_parser.set_defaults(func = self.register)

        run_parser = subparsers.add_parser("run")
        run_parser.set_defaults(func = self.run)

        args = parser.parse_args()
        args.func(args)

        # Wake up periodically to handle signals, instead of going straight into join
        while not self._stopping.is_set():
            self._stopping.wait(timeout = 1)

        self.simulator.join()


def main():
    cli = SimulatorCli()

    def handler(*args, **kwargs):
        log.info("Stopping...")
        cli.stop()

    signal.signal(signal.SIGINT, handler)

    cli.main()
