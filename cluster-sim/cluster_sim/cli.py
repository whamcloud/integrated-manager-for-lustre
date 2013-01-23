#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import argparse
import json
import logging
import signal
import threading

from cluster_sim.log import log
from cluster_sim.simulator import ClusterSimulator
import sys

from chroma_agent.agent_daemon import daemon_log
import os
import requests

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

    def _acquire_token(self, url, username, password, credits):
        """
        Localised use of the REST API to acquire a server registration token.
        """
        session = requests.session()
        session.headers = {"Accept": "application/json"}
        session.verify = False

        response = session.get("%sapi/session/" % url)
        if not response.ok:
            raise RuntimeError("Failed to open session")
        session.headers['X-CSRFToken'] = response.cookies['csrftoken']
        session.cookies['csrftoken'] = response.cookies['csrftoken']
        session.cookies['sessionid'] = response.cookies['sessionid']

        response = session.post("%sapi/session/" % url,
            data = json.dumps({'username': username, 'password': password}),
            headers = {"Content-type": "application/json"})
        if not response.ok:
            raise RuntimeError("Failed to authenticate")

        response = session.post("%sapi/registration_token/" % url, data = json.dumps({'credits': credits}))
        if not response.status_code == 201:
            print response.content
            raise RuntimeError("Error %s acquiring token" % response.status_code)
        token_uri = response.headers['location']
        response = session.get(token_uri)
        return response.json()['secret']

    def register(self, args):
        server_count = len(self.simulator.servers)
        if args.secret:
            secret = args.secret
        elif args.username and args.password:
            secret = self._acquire_token(args.url, args.username, args.password, server_count)
        else:
            sys.stderr.write("""
            Must pass either --secret or --username and --password
            """)
            sys.exit(-1)

        self.simulator = ClusterSimulator(args.config, args.url)
        log.info("Registering %s servers in %s/" % (server_count, args.config))
        self.simulator.register_all(secret)

    def run(self, args):
        self.simulator = ClusterSimulator(args.config, args.url)
        log.info("Running %s servers in %s/" % (len(self.simulator.servers), args.config))
        self.simulator.start_all()

    def stop(self):
        self.simulator.stop()
        self._stopping.set()

    def main(self):
        log.addHandler(logging.StreamHandler())

        # Usually on our Intel laptops https_proxy is set, and needs to be unset for tests,
        # but let's not completely rule out the possibility that someone might want to run
        # the tests on a remote system using a proxy.
        if 'https_proxy' in os.environ:
            sys.stderr.write("Warning: Using proxy %s from https_proxy" % os.environ['https_proxy'] +
                             " environment variable, you probably don't want that\n")

        parser = argparse.ArgumentParser(description = "Cluster simulator")
        parser.add_argument('--config', required = False, help = "Simulator configuration/state directory", default = "cluster_sim")
        parser.add_argument('--url', required = False, help = "Chroma manager URL", default = "https://localhost:8000/")
        subparsers = parser.add_subparsers()
        setup_parser = subparsers.add_parser("setup")
        setup_parser.add_argument('--server_count', required = False, help = "Number of simulated storage servers", default = '8')
        setup_parser.add_argument('--volume_count', required = False, help = "Number of simulated storage devices, defaults to twice the number of servers")
        setup_parser.set_defaults(func = self.setup)

        register_parser = subparsers.add_parser("register", help = "Provide a secret for registration, or provide API credentials for the simulator to acquire a token itself")
        register_parser.add_argument('--secret', required = False, help = "Registration token secret")
        register_parser.add_argument('--username', required = False, help = "API username")
        register_parser.add_argument('--password', required = False, help = "API password")
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
