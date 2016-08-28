#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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


import glob
import json
import traceback
import os
import threading
import time
from requests import ConnectionError

from chroma_agent.agent_client import CryptoClient, AgentClient, HttpError, Session
from chroma_agent.copytool_monitor import CopytoolMonitor

from cluster_sim.utils import Persisted
from cluster_sim.fake_action_plugins import FakeActionPlugins
from cluster_sim.fake_controller import FakeController
from cluster_sim.fake_client import FakeClient
from cluster_sim.fake_cluster import FakeCluster
from cluster_sim.fake_devices import FakeDevices
from cluster_sim.fake_power_control import FakePowerControl
from cluster_sim.fake_server import FakeServer
from cluster_sim.fake_device_plugins import FakeDevicePlugins
from cluster_sim.fake_hsm_coordinator import FakeHsmCoordinator
from cluster_sim.fake_hsm_copytool import FakeHsmCopytool
from cluster_sim.log import log

# Ensure copytool logging goes to sim log
from chroma_agent import copytool_monitor
copytool_monitor.copytool_log = log


class UnregisteredCopytoolError(Exception):
    pass


class ClusterSimulator(Persisted):
    """
    Create the global fakes and the per-server fakes, and publish
    start/stop/register operations for each simulated agent.
    """
    filename = 'simulator.json'
    default_state = {
        'packages': {
            'server': {},
            'worker': {}
        }
    }

    def __init__(self, folder, url):
        self.folder = folder
        super(ClusterSimulator, self).__init__(folder)

        self.url = url + "agent/"

        if folder and not os.path.exists(folder):
            os.makedirs(folder)

        self.lustre_clients = {}
        self.devices = FakeDevices(folder)
        self.power = FakePowerControl(folder, self.poweron_server, self.poweroff_server)
        self.servers = {}
        self.clusters = {}
        self.controllers = {}
        self.coordinators = {}
        self.copytools = {}
        self.copytool_monitors = {}

        self._load_controllers()
        self._load_servers()

    def update_packages(self, packages, node_type='server'):
        log.info("Updating packages: %s" % packages)
        for k, v in packages.items():
            self.state['packages'][node_type][k] = v
        self.save()

        # The agent only reports new versions at the start of sessions
        # IRL this is valid because when we install updates on the manager
        # we restart the manager servers, causing new sessions.  In simulation,
        # we don't control the manager, so instead restart the AgentClient instances.
        for fqdn in self.servers.keys():
            self.stop_server(fqdn)
            self.start_server(fqdn)

    def available_packages(self, node_type='server'):
        return self.state['packages'][node_type]

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
                conf['network_interfaces'],
                conf['worker'],
                conf['client_mounts'])

    def _load_controllers(self):
        for controller_conf in glob.glob("%s/fake_controller_*.json" % self.folder):
            conf = json.load(open(controller_conf))
            self.controllers[conf['controller_id']] = FakeController(self.folder, conf['controller_id'])

    def _create_server(self, i, nid_count):
        interface_names = ['tcp', 'o2ib']
        nid_tuples = []
        nodename = "test%.3d" % i
        fqdn = "%s.localdomain" % nodename
        x, y = (i / 256, i % 256)
        for network in range(0, nid_count):
            name = interface_names[network % len(interface_names)]
            address = '10.%d.%d.%d' % (network, x, y)
            nid_tuples.append((address, name, network))

        log.info("_create_server: %s" % fqdn)

        server = FakeServer(self, self._get_cluster_for_server(i), i, fqdn, nodename, nid_tuples)
        self.servers[fqdn] = server

        self.power.add_server(fqdn)

        return server

    def _create_worker(self, i, nid_count):
        nid_tuples = []
        nodename = "worker%.3d" % i
        fqdn = "%s.localdomain" % nodename
        x, y = (i / 256, i % 256)
        for network in range(0, nid_count):
            nid_tuples.append(('10.%d.%d.%d' % (network, x, y), 'tcp', network))

        log.info("_create_worker: %s" % fqdn)

        # Use -1 as the special cluster for workers
        worker = FakeServer(self, self._get_cluster_for_server(-1),
                            i, fqdn, nodename, nid_tuples, worker=True)
        self.servers[fqdn] = worker

        return worker

    def configure_hsm_copytool(self, server, **kwargs):
        copytool = FakeHsmCopytool(self.folder, server.fqdn, **kwargs)
        self.copytools[copytool.id] = copytool

    def unconfigure_hsm_copytool(self, id):
        self.copytools[id].stop()
        self.copytools[id].delete()
        del self.copytools[id]

    def start_monitored_copytool(self, server, id):
        copytool = self.copytools[id]
        coordinator = self.coordinators[copytool.filesystem]

        client = CryptoClient(self.url + "copytool_event/", server.crypto,
                              server.fqdn)
        monitor = CopytoolMonitor(client, copytool)
        self.copytool_monitors[id] = monitor
        self.copytool_monitors[id].start()
        copytool.start(coordinator)

    def stop_monitored_copytool(self, id):
        try:
            self.copytools[id].stop()
        except KeyError:
            log.error("Attempt to stop unknown copytool: %s" % id)

        try:
            self.copytool_monitors[id].stop()
        except KeyError:
            log.error("Attempt to stop unknown copytool monitor: %s" % id)

    def start_hsm_copytools(self):
        for conf in glob.glob("%s/fake_hsm_copytool-*.json" % self.folder):
            with open(conf) as f:
                data = json.load(f)
                server = self.servers[data['server']]
                self.configure_hsm_copytool(server, **data['copytool'])
                self.start_monitored_copytool(server, data['copytool']['id'])

    def start_hsm_coordinators(self):
        for conf in glob.glob("%s/fake_hsm_coordinator-*.json" % self.folder):
            fsname = json.load(open(conf))['filesystem']
            coordinator = FakeHsmCoordinator(self, fsname)
            self.coordinators[fsname] = coordinator
            coordinator.start()

    def control_hsm_coordinator(self, fsname, control_value):
        if not fsname in self.coordinators:
            coordinator = FakeHsmCoordinator(self, fsname)
            self.coordinators[fsname] = coordinator

        self.coordinators[fsname].control(control_value)

    def setup(self, server_count, worker_count, volume_count, nid_count, cluster_size, pdu_count, su_size):
        """

        :param server_count: How many servers in total should exist after call
        :param worker_count: How many worker nodes in total should exist after call
        :param volume_count: How many volumes in total should exist after call
        :param nid_count: How many NIDs each server should have
        :param cluster_size: How many servers per corosync cluster
        :param pdu_count: How many PDUs in total
        :param su_size: How many servers per SU, or zero for no controllers + SAN-style volumes
        :return:
        """
        self.state['cluster_size'] = cluster_size
        self.save()

        # Packages which the FakeServers will report as available
        self.state['packages'] = {
            'server': {
                'lustre': (0, '2.1.4', '1', 'x86_64'),
                'lustre-osd-ldiskfs': (0, '2.1.4', '1', 'x86_64'),
                'lustre-dkms': (0, '2.1.4', '1', 'x86_64'),
                'lustre-osd-zfs-mount': (0, '2.1.4', '1', 'x86_64'),
                'kernel-devel-3.10.0-327.28.2.el7_lustre': (0, '2.6.32', '1', 'x86_64'),
                'zfs': (0, '0.6.5.3', '1', 'x86_64')
            },
            'worker': {
                'lustre-client': (0, '2.5.0', '1', 'x86_64'),
                'lustre-client-modules': (0, '2.5.0', '1', 'x86_64')
            }
        }
        for packages in self.state['packages'].values():
            packages['chroma-agent'] = (0, '3.0.1', '1', 'x86_64')
            packages['chroma-agent-management'] = (0, '3.0.1', '1', 'x86_64')
        self.save()

        self.power.setup(pdu_count)

        if su_size:
            # Series of SUs, blocks of one controller with several servers
            if server_count % su_size != 0:
                raise RuntimeError("server_count not a multiple of su_size")
            su_count = server_count / su_size
            if volume_count % su_count != 0:
                raise RuntimeError("volume_count not a multiple of su_count")

            for i in range(0, su_count):
                self.add_su(server_count / su_count, volume_count / su_count, nid_count)
        else:
            # SAN-style LUNs visible to all servers
            for i in range(0, server_count):
                self._create_server(i, nid_count)

            self.devices.add_presented_luns(volume_count, self.servers.keys())

        for i in range(0, worker_count):
            self._create_worker(i, nid_count)

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
        """
        In this context SU stands for 'scalable unit', a notional unit of storage hardware
        consisting of some servers and a shared storage controller.

        :param server_count: How many servers in the SU
        :param volume_count: How many volumes in the SU (visible to all servers in the SU)
        :param nid_count: How many LNET NIDs should each server have
        """
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

    def register_all(self, server_secret, worker_secret):
        register_count = 0
        for fqdn, server in self.servers.items():
            if server.crypto.certificate_file is None:
                if server.is_worker:
                    self.register(fqdn, worker_secret)
                else:
                    self.register(fqdn, server_secret)
                register_count += 1
            else:
                self.start_server(fqdn)

        self.post_server_start()

        # Useful for some callers to know if servers were registered or
        # just started.
        return register_count

    def register(self, fqdn, secret):
        try:
            log.debug("register %s" % fqdn)
            server = self.servers[fqdn]

            if server.agent_is_running:
                # e.g. if the server was added then force-removed then re-added
                server.shutdown_agent()

            if not server.is_worker and not self.power.server_has_power(fqdn):
                raise RuntimeError("Not registering %s, none of its PSUs are powered" % fqdn)

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

    def reboot_server(self, fqdn):
        log.debug("reboot %s" % fqdn)
        server = self.servers[fqdn]
        if not server.running:
            server.startup()
        else:
            server.shutdown(reboot = True)

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
        log.info("Stopping")
        self.power.stop()
        for group in ['coordinators', 'copytools', 'copytool_monitors', 'servers']:
            for thread in getattr(self, group).values():
                thread.stop()

    def join(self):
        log.info("Joining...")
        self.power.join()
        for group in ['coordinators', 'copytools', 'copytool_monitors', 'servers']:
            for thread in getattr(self, group).values():
                thread.join()
        log.info("Joined")

    def pre_server_start(self):
        self.power.start()

    def post_server_start(self):
        if len(self.servers) < 1:
            log.info("No servers started; skipping post_server_start()")
            return

        self.start_hsm_coordinators()
        self.start_hsm_copytools()

    def start_all(self):
        self.pre_server_start()

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

        self.post_server_start()

    def set_log_rate(self, fqdn, rate):
        log.info("Set log rate for %s to %s" % (fqdn, rate))
        self.servers[fqdn].log_rate = rate

    def poll_fake_controller(self, controller_id):
        """
        For use by the simulator_controller storage plugin: query a particular fake controller
        """
        try:
            controller = self.controllers[int(controller_id)]
        except KeyError:
            log.error("Controller '%s' not found in %s" % (controller_id, self.controllers.keys()))
            raise
        else:
            return controller.poll()

    def format_block_device(self, fqdn, path, filesystem_type):
        self.devices.format_local(fqdn, path, filesystem_type)
