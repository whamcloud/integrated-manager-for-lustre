#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import logging
from chroma_agent.agent_client import AgentClient
from chroma_agent.crypto import Crypto
from chroma_core.services.cluster_sim.fakes import FakeActionPlugins, FakeDevicePlugins, FakeCluster, FakeDevices, FakeServer, FakeClient

import os

log = logging.getLogger(__name__)

handler = logging.FileHandler('cluster_sim.log')
handler.setFormatter(logging.Formatter("[%(asctime)s: %(levelname)s/%(name)s] %(message)s"))

log.addHandler(handler)
log.setLevel(logging.DEBUG)


class ClusterSimulator(object):
    def __init__(self, N, folder, url):
        self.N = N
        self.folder = folder
        self.url = url + "agent/"

        if not os.path.exists(folder):
            os.makedirs(folder)

        self.lustre_clients = {}
        self.cluster = FakeCluster(folder)
        self.devices = FakeDevices(folder)
        self.servers = {}
        for n in range(0, self.N):
            nodename = "test%.3d" % n
            fqdn = "%s.localdomain" % nodename
            nids = ["10.0.%d.%d@tcp0" % (n / 256, n % 256)]

            server = self.servers[fqdn] = FakeServer(self.folder, self.devices, self.cluster, fqdn, nodename, nids)

            class FakeCrypto(Crypto):
                FOLDER = os.path.join(self.folder, "%s_crypto" % server.fqdn)

            if not os.path.exists(FakeCrypto.FOLDER):
                os.makedirs(FakeCrypto.FOLDER)
            server.crypto = FakeCrypto()

        self._clients = {}

    def register_all(self):
        for fqdn in self.servers.keys():
            self.register(fqdn)

    def register(self, fqdn):
        log.debug("register %s" % fqdn)
        if fqdn in self._clients:
            self.stop_server(fqdn)
        server = self.servers[fqdn]
        client = AgentClient(
            url = self.url + "register/xyz/",
            action_plugins = FakeActionPlugins(self, server),
            device_plugins = FakeDevicePlugins(server),
            server_properties = server,
            crypto = server.crypto
        )
#        try:
        registration_result = client.register()
        server.crypto.install_certificate(registration_result['certificate'])
        #self.start_server(server.fqdn)
        return registration_result
#        except Exception:
#            # probably it's already registered
#            # TODO: handle this case specifically
#            pass

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
        del self._clients[fqdn]

        if shutdown:
            self.cluster.leave(self.servers[fqdn].nodename)

    def start_server(self, fqdn):
        log.debug("start %s" % fqdn)
        assert fqdn not in self._clients
        server = self.servers[fqdn]
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
        log.debug("join me")
        log.info("Joining...")
        for client in self._clients.values():
            client.join()
        self._clients.clear()
        log.info("Joined")

    def start_all(self):
        log.debug("start all")
        for fqdn in self.servers.keys():
            self.start_server(fqdn)
