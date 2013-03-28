#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import glob
import json
import traceback
import os
import threading
import time
from requests import ConnectionError

from chroma_agent.agent_client import AgentClient, HttpError, Session

from cluster_sim.utils import Persisted
from cluster_sim.fake_action_plugins import FakeActionPlugins
from cluster_sim.fake_controller import FakeController
from cluster_sim.fake_client import FakeClient
from cluster_sim.fake_cluster import FakeCluster
from cluster_sim.fake_devices import FakeDevices
from cluster_sim.fake_power_control import FakePowerControl
from cluster_sim.fake_server import FakeServer
from cluster_sim.fake_device_plugins import FakeDevicePlugins
from cluster_sim.log import log


class ClusterSimulator(Persisted):
    """
    Create the global fakes and the per-server fakes, and publish
    start/stop/register operations for each simulated agent.
    """
    filename = 'simulator.json'

    def __init__(self, folder, url):
        self.folder = folder
        super(ClusterSimulator, self).__init__(folder)

        self.url = url + "agent/"

        if not os.path.exists(folder):
            os.makedirs(folder)

        self.lustre_clients = {}
        self.devices = FakeDevices(folder)
        self.power = FakePowerControl(folder, self.poweron_server, self.poweroff_server)
        self.servers = {}
        self.clusters = {}
        self.controllers = {}

        self._load_servers()

    def _get_cluster_for_server(self, server_id):
        cluster_id = server_id / self.state['cluster_size']
        try:
            return self.clusters[cluster_id]
        except KeyError:
            cluster = self.clusters[cluster_id] = FakeCluster(self.folder, cluster_id)
            return cluster

    def get_cluster(self, fqdn):
        return self._get_cluster_for_server(self.servers[fqdn].id)

    def _load_servers(self):
        for server_conf in glob.glob("%s/fake_server_*.json" % self.folder):
            conf = json.load(open(server_conf))
            self.servers[conf['fqdn']] = FakeServer(
                self,
                self._get_cluster_for_server(conf['id']),
                conf['id'],
                conf['fqdn'],
                conf['nodename'],
                conf['nids'])

    def _create_server(self, i, nid_count):
        nids = []
        nodename = "test%.3d" % i
        fqdn = "%s.localdomain" % nodename
        x, y = (i / 256, i % 256)
        for network in range(0, nid_count):
            nids.append("10.%d.%d.%d@tcp%d" % (network, x, y, network))

        log.info("_create_server: %s" % fqdn)

        server = FakeServer(self, self._get_cluster_for_server(i), i, fqdn, nodename, nids)
        self.servers[fqdn] = server

        self.power.add_server(fqdn)

        return server

    def setup(self, server_count, volume_count, nid_count, cluster_size, psu_count):
        self.state['cluster_size'] = cluster_size
        self.save()

        self.power.setup(psu_count)

        for i in range(0, server_count):
            self._create_server(i, nid_count)

        # SAN-style LUNs visible to all servers
        self.devices.add_presented_luns(volume_count, self.servers.keys())

    def clear_clusters(self):
        for cluster in self.clusters.values():
            cluster.clear_resources()

    def remove_server(self, fqdn):
        log.info("remove_server %s" % fqdn)

        self.stop_server(fqdn, shutdown = True)
        server = self.servers[fqdn]
        assert not server.agent_is_running

        self.devices.remove_presentations(fqdn)

        self.power.remove_server(fqdn)

        server.crypto.delete()
        server.delete()
        del self.servers[fqdn]

    def remove_all_servers(self):
        # Ask them all to stop
        for fqdn, server in self.servers.items():
            if server.agent_is_running:
                server.shutdown_agent()

        # Wait for them to stop and complete removal
        for fqdn in self.servers.keys():
            self.remove_server(fqdn)

    def add_server(self, nid_count):
        i = len(self.servers)
        server = self._create_server(i, nid_count)
        return server.fqdn

    def add_su(self, server_count, volume_count, nid_count):
        try:
            fqdns = [self.add_server(nid_count) for _ in range(0, server_count)]
            serials = self.devices.add_presented_luns(volume_count, fqdns)

            if self.controllers:
                controller_id = max(self.controllers.keys()) + 1
            else:
                controller_id = 1
            controller = FakeController(self.folder, controller_id)
            for serial in serials:
                device = self.devices.get_device(serial)
                controller.add_lun(device['serial_80'], device['size'])
            self.controllers[controller_id] = controller

            return {
                'fqdns': fqdns,
                'serials': serials,
                'controller_id': controller_id
            }
        except Exception:
            print traceback.format_exc()
            raise

    def register_all(self, secret):
        self.power.start()
        for fqdn, server in self.servers.items():
            if server.crypto.certificate_file is None:
                self.register(fqdn, secret)
            else:
                self.start_server(fqdn)

    def register(self, fqdn, secret):
        try:
            log.debug("register %s" % fqdn)
            server = self.servers[fqdn]
            if server.agent_is_running:
                server.shutdown_agent()
            if not self.power.server_has_power(fqdn):
                log.warning("Not registering %s, none of its PSUs are powered" % fqdn)
                return
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
        except Exception:
            log.error(traceback.format_exc())

    def register_many(self, fqdns, secret):
        simulator = self

        class RegistrationThread(threading.Thread):
            def __init__(self, fqdn, secret):
                super(RegistrationThread, self).__init__()
                self.fqdn = fqdn
                self.secret = secret

            def run(self):
                self.result = simulator.register(self.fqdn, self.secret)

        threads = []
        log.debug("register_many: spawning threads")
        for fqdn in fqdns:
            thread = RegistrationThread(fqdn, secret)
            thread.start()
            threads.append(thread)

        for i, thread in enumerate(threads):
            thread.join()
            log.debug("register_many: joined %s/%s" % (i + 1, len(threads)))

        return [t.result for t in threads]

    def poweroff_server(self, fqdn):
        self.stop_server(fqdn, shutdown = True, simulate_shutdown = True)

    def poweron_server(self, fqdn):
        self.start_server(fqdn, simulate_bootup = True)

    def stop_server(self, fqdn, shutdown = False, simulate_shutdown = False):
        """
        :param shutdown: Whether to treat this like a server shutdown (leave the
         HA cluster) rather than just an agent shutdown.
        :param simulate_shutdown: Whether to simulate a shutdown, delays and all
        """
        log.debug("stop %s" % fqdn)
        server = self.servers[fqdn]
        if not server.running:
            log.debug("not running")
            return

        if shutdown:
            server.shutdown(simulate_shutdown)
        else:
            server.shutdown_agent()

    def start_server(self, fqdn, simulate_bootup = False):
        """
        :param simulate_bootup: Whether to simulate a bootup, delays and all
        """
        log.debug("start %s" % fqdn)
        server = self.servers[fqdn]
        if server.running and not simulate_bootup:
            raise RuntimeError("Can't start %s, it is already running" % fqdn)
        server.startup(simulate_bootup)

    def get_lustre_client(self, client_address):
        try:
            client = self.lustre_clients[client_address]
        except KeyError:
            client = self.lustre_clients[client_address] = FakeClient(self.folder, client_address, self.devices, self.clusters)
        return client

    def unmount_lustre_clients(self):
        for client in self.lustre_clients.values():
            client.unmount_all()

    def stop(self):
        log.debug("stop me")
        log.info("Stopping")
        for server in self.servers.values():
            server.stop()
        self.power.stop()

    def join(self):
        log.info("Joining...")
        for server in self.servers.values():
            server.join()
        log.info("Joined")

    def start_all(self):
        self.power.start()
        # Spread out starts to avoid everyone doing sending their update
        # at the same moment

        if len(self.servers):
            delay = Session.POLL_PERIOD / float(len(self.servers))

            log.debug("Start all (%.2f dispersion)" % delay)

            for i, fqdn in enumerate(self.servers.keys()):
                self.start_server(fqdn)
                if i != len(self.servers) - 1:
                    time.sleep(delay)
        else:
            log.info("start_all: No servers yet")

    def set_log_rate(self, fqdn, rate):
        log.info("Set log rate for %s to %s" % (fqdn, rate))
        self.servers[fqdn].log_rate = rate

    def poll_fake_controller(self, controller_id):
        """
        For use by the simulator_controller storage plugin: query a particular fake controller
        """
        data = self.controllers[controller_id].poll()
        return data
