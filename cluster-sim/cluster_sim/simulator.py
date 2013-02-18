#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import glob
import json
import datetime
import os

from chroma_agent.agent_client import AgentClient, HttpError
from chroma_agent.crypto import Crypto

from cluster_sim.fake_action_plugins import FakeActionPlugins
from cluster_sim.fake_client import FakeClient
from cluster_sim.fake_cluster import FakeCluster
from cluster_sim.fake_devices import FakeDevices
from cluster_sim.fake_server import FakeServer
from cluster_sim.fake_device_plugins import  FakeDevicePlugins
from cluster_sim.log import log

from requests import ConnectionError


class ClusterSimulator(object):
    """
    Create the global fakes and the per-server fakes, and publish
    start/stop/register operations for each simulated agent.
    """
    def __init__(self, folder, url):
        self.folder = folder
        self.url = url + "agent/"

        if not os.path.exists(folder):
            os.makedirs(folder)

        self.lustre_clients = {}
        self.cluster = FakeCluster(folder)
        self.devices = FakeDevices(folder)
        self.servers = {}

        self._load_servers()
        self._clients = {}

    def _load_servers(self):
        for server_conf in glob.glob("%s/fake_server_*.json" % self.folder):
            conf = json.load(open(server_conf))
            server = self.servers[conf['fqdn']] = FakeServer(self.folder, self.devices, self.cluster, conf['fqdn'], conf['nodename'], conf['nids'])

            crypto_folder = os.path.join(self.folder, "%s_crypto" % server.fqdn)
            if not os.path.exists(crypto_folder):
                os.makedirs(crypto_folder)
            server.crypto = Crypto(crypto_folder)

    def setup(self, server_count, volume_count, nid_count):
        for n in range(0, server_count):
            nids = []
            nodename = "test%.3d" % n
            fqdn = "%s.localdomain" % nodename
            x, y = (n / 256, n % 256)
            for network in range(0, nid_count):
                nids.append("10.%d.%d.%d@tcp%d" % (network, x, y, network))

            FakeServer(self.folder, self.devices, self.cluster, fqdn, nodename, nids)

        self._load_servers()

        self.devices.setup(volume_count)

    def register_all(self, secret):
        for fqdn, server in self.servers.items():
            if server.crypto.certificate_file is None:
                self.register(fqdn, secret)
            else:
                self.start_server(fqdn)

    def register(self, fqdn, secret):
        log.debug("register %s" % fqdn)
        if fqdn in self._clients:
            self.stop_server(fqdn)
        server = self.servers[fqdn]
        client = AgentClient(
            url = self.url + "register/%s/" % secret,
            action_plugins = FakeActionPlugins(self, server),
            device_plugins = FakeDevicePlugins(server),
            server_properties = server,
            crypto = server.crypto
        )

        try:
            registration_result = client.register()
        except ConnectionError as e:
            log.error("Registration connection failed for %s: %s" % (fqdn, e))
            return
        except HttpError as e:
            log.error("Registration request failed for %s: %s" % (fqdn, e))
            return
        server.crypto.install_certificate(registration_result['certificate'])

        # Immediately start the agent after registration, to pick up the
        # setup actions that will be waiting for us on the manager.
        self.start_server(fqdn)
        return registration_result

    def stop_server(self, fqdn, shutdown = False):
        """
        :param shutdown: Whether to treat this like a server shutdown (leave the
         HA cluster) rather than just an agent shutdown.
        """
        log.debug("stop %s" % fqdn)
        if not fqdn in self._clients:
            log.debug("not running")
            return

        self._clients[fqdn].stop()
        self._clients[fqdn].join()
        # Have to join the reader explicitly, normal AgentClient code
        # skips it because it's slow to join (waits for long-polling GET to complete)
        self._clients[fqdn].reader.join()
        if fqdn in self._clients:
            del self._clients[fqdn]

        if shutdown:
            self.cluster.leave(self.servers[fqdn].nodename)

    def start_server(self, fqdn):
        log.debug("start %s" % fqdn)
        assert fqdn not in self._clients
        server = self.servers[fqdn]
        server.boot_time = datetime.datetime.utcnow()
        if server.crypto.certificate_file is None:
            log.warning("Not starting %s, it is not registered" % fqdn)
            return
        client = AgentClient(
            url = self.url + "message/",
            action_plugins = FakeActionPlugins(server, self),
            device_plugins = FakeDevicePlugins(server),
            server_properties = server,
            crypto = server.crypto)
        client.start()
        self._clients[fqdn] = client

        self.cluster.join(self.servers[fqdn].nodename)

    def get_lustre_client(self, client_address):
        try:
            client = self.lustre_clients[client_address]
        except KeyError:
            client = self.lustre_clients[client_address] = FakeClient(self.folder, client_address, self.devices, self.cluster)
        return client

    def unmount_lustre_clients(self):
        for client in self.lustre_clients.values():
            client.unmount_all()

    def stop(self):
        log.debug("stop me")
        log.info("Stopping")
        for client in self._clients.values():
            client.stop()

    def join(self):
        log.info("Joining...")
        for client in self._clients.values():
            client.join()
        self._clients.clear()
        log.info("Joined")

    def start_all(self):
        log.debug("start all")
        for fqdn in self.servers.keys():
            self.start_server(fqdn)
