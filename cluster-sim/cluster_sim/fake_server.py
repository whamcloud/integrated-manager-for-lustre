# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import tempfile
import time
import datetime
import json
import random
import uuid
import os
import threading
from collections import defaultdict

from chroma_agent.crypto import Crypto
from chroma_agent.agent_client import AgentClient

from cluster_sim.log import log
from cluster_sim import utils
from chroma_agent.device_plugins.action_runner import CallbackAfterResponse
from cluster_sim.fake_action_plugins import FakeActionPlugins
from cluster_sim.fake_device_plugins import FakeDevicePlugins
from chroma_agent.chroma_common.lib.agent_rpc import agent_result, agent_result_ok
from chroma_agent.chroma_common.lib.date_time import IMLDateTime

# Simulated duration, in seconds, from the time a server shutdown is issued
# until it's stopped. When simulating a shutdown, it will always take at
# least this long.
MIN_SHUTDOWN_DURATION = 5  # 10
# Simulated duration, in seconds, from the time a server is started until
# it's running. When simulating a startup, it will always take at least
# this long.
MIN_STARTUP_DURATION = 5  # 20


class PacemakerState(utils.DictStruct):
    def __init__(self, state):
        super(PacemakerState, self).__init__()
        self['state'] = state

    @property
    def state(self):
        return self['state']

    @state.setter
    def state(self, value):
        self['state'] = value


class CorosyncState(PacemakerState):
    def __init__(self, state, mcast_port):
        super(CorosyncState, self).__init__(state)
        self['mcast_port'] = mcast_port

    @property
    def mcast_port(self):
        return self['mcast_port']

    @mcast_port.setter
    def mcast_port(self, value):
        self['mcast_port'] = value


class FakeServer(utils.Persisted):
    """Represent a single storage server.  Initialized with an arbitrary
    hostname and NIDs, subsequently manages/modifies its own /proc/ etc.
    """
    default_state = {
        'worker': False,
        'shutting_down': False,
        'starting_up': False,
        'lnet_loaded': False,
        'lnet_up': False,
        'stats': None,
        'packages': {},
        'client_mounts': {},
        'corosync': CorosyncState('stopped', 3000),
        'pacemaker': PacemakerState('stopped')
    }

    def __init__(self, simulator, fake_cluster, server_id, fqdn, nodename, nid_tuples_or_network_interfaces, worker=False, client_mounts=None):
        self.fqdn = fqdn

        super(FakeServer, self).__init__(simulator.folder)

        self.nodename = nodename

        # When reloaded from a file the network interfaces are presented as a dict but when created from code they
        # are represented as nid_tuples.
        if type(nid_tuples_or_network_interfaces) is dict:
            self.network_interfaces = nid_tuples_or_network_interfaces
        else:
            self.network_interfaces = {}
            interface_no = 0
            for nid in nid_tuples_or_network_interfaces:
                self.network_interfaces[nid[0]] = {'interface_no': interface_no,
                                                   'type': nid[1],
                                                   'lnd_type': nid[1],
                                                   'lnd_network': nid[2]}
                interface_no += 1

        self.boot_time = IMLDateTime.utcnow()
        self.id = server_id

        self.log_rate = 0
        self._log_messages = []
        self._simulator = simulator
        self._devices = simulator.devices
        self._cluster = fake_cluster

        self._lock = threading.Lock()
        self._agent_client = None

        self._cluster.join(nodename, fqdn=fqdn)

        if simulator.folder:
            # If simulator is persistent, save Crypto in same place
            crypto_folder = os.path.join(simulator.folder, "%s_crypto" % self.fqdn)
        else:
            # If simulator is ephemeral, create temp dir for Crypto
            crypto_folder = tempfile.mkdtemp()

        if not os.path.exists(crypto_folder):
            os.makedirs(crypto_folder)
        self.crypto = Crypto(crypto_folder)

        if not client_mounts:
            client_mounts = {}

        self.state['id'] = server_id
        self.state['network_interfaces'] = self.network_interfaces
        self.state['nodename'] = nodename
        self.state['fqdn'] = fqdn
        self.state['worker'] = worker
        self.state['client_mounts'] = client_mounts
        self.state['packages']['chroma-agent'] = self._simulator.available_packages(self.node_type)['chroma-agent']    # The agent is installed at this point.
        self.save()

    @property
    def is_worker(self):
        with self._lock:
            return self.state['worker']

    @property
    def node_type(self):
        return 'worker' if self.is_worker else 'server'

    @property
    def lustre_client_mounts(self):
        mounts = []
        with self._lock:
            for mountspec, mountpoint in self.state['client_mounts'].items():
                mounts.append({'mountspec': mountspec, 'mountpoint': mountpoint})
            return mounts

    def add_client_mount(self, mountspec, mountpoint):
        fsname = mountspec.split(':/')[1]
        mountpoint = "%s/%s" % (mountpoint, fsname)
        self.start_lnet()
        with self._lock:
            self.state['client_mounts'][mountspec] = mountpoint
            self.save()
        log.debug("Mounted %s on %s" % (mountspec, mountpoint))

    def del_client_mount(self, mountspec):
        with self._lock:
            try:
                del self.state['client_mounts'][mountspec]
                self.save()
            except KeyError:
                pass
        log.debug("Unmounted %s" % mountspec)

    @property
    def nids(self):
        nids = []

        for inet4_address in self.network_interfaces.keys():
            interface = self.network_interfaces[inet4_address]

            if interface['lnd_network'] is not None:
                nids.append("%s@%s%s" % (inet4_address, interface['type'], interface['lnd_network']))

        return nids

    def update_profile(self, profile):
        with self._lock:
            self.state['profile_name'] = profile['name']
            self.save()

        return agent_result_ok

    def restart_agent(self):
        def _restart():
            # FIXME: don't actually want to simulate_shutdown but otherwise it tries to join from the current thread
            self.shutdown(simulate_shutdown=True, reboot=True)

        raise CallbackAfterResponse(None, _restart)

    def scan_packages(self):
        packages = {}
        for package, available_version in self._simulator.available_packages(self.node_type).items():
            try:
                installed = [self.get_package_version(package)]
            except KeyError:
                installed = []

            packages[package] = {
                'available': [available_version],
                'installed': installed
            }

        return {'e2fsprogs': packages}

    def install_packages(self, repos, packages):
        for package in packages:
            try:
                self.state['packages'][package] = self._simulator.available_packages(self.node_type)[package]
            except KeyError:
                raise RuntimeError("Package '%s' not found (available: %s)!" %
                                   (package, self._simulator.available_packages(self.node_type)))

        self.save()

        return agent_result(self.scan_packages())

    def get_package_version(self, package):
        return self.state['packages'][package]

    def inject_log_message(self, message):
        log.debug("Injecting log message %s/%s" % (self.fqdn, message))
        self._log_messages.append(
            {
                'source': 'cluster_sim',
                'severity': 1,
                'facility': 1,
                'message': message,
                'datetime': IMLDateTime.utcnow().isoformat()
            })

    def pop_log_messages(self):
        messages = self._log_messages

        d = datetime.datetime.now()
        messages.extend([
            {
                'source': 'cluster_sim',
                'severity': 1,
                'facility': 1,
                'message': "%s %s %s" % (self.fqdn, d, a),
                'datetime': IMLDateTime.utcnow().isoformat()
            } for a in range(0, self.log_rate)])

        self._log_messages = []
        return messages

    def _proc_path_to_target(self, path):
        """Look up a target dict from a /proc/ path"""

        parts = path.split("/")[1:]
        if parts[3] == 'lov':
            # /proc/fs/lustre/lov/testfs-MDT0000-mdtlov/stripesize
            mdt_name = parts[4].rsplit("-", 1)[0]
            for target in self._targets_started_here:
                if target['label'] == mdt_name:
                    return target

            raise RuntimeError("%s: Cannot get proc information for %s, it's not started here (targets here are: %s)" % (
                self.fqdn, mdt_name,
                [t['label'] for t in self._targets_started_here]))

        elif parts[3] == 'obdfilter':
            # /proc/fs/lustre/obdfilter/testfs-OST0000/writethrough_cache_enable
            ost_name = parts[4]
            for target in self._targets_started_here:
                if target['label'] == ost_name:
                    return target

            raise RuntimeError("%s: Cannot get proc information for %s, it's not started here (targets here are: %s)" % (
                self.fqdn, ost_name,
                [t['label'] for t in self._targets_started_here]))

        elif parts[3] == 'mdt':
            # /proc/fs/lustre/mdt/testfs-MDT0000/hsm_control
            mdt_name = parts[4]
            for target in self._targets_started_here:
                if target['label'] == mdt_name:
                    return target

        raise NotImplementedError("Simulator cannot resolve '%s' to target" % path)

    def _proc_path_to_conf_param(self, configs, path):
        """Resolve a /proc/foo/bar to a foo-MDT0000.bar.baz and look it up
        in the `configs` dict, or substitute a default if it's not set"""

        LOV_DEFAULTS = {
            'stripesize': "1"
        }

        OBDFILTER_DEFAULTS = {
            'writethrough_cache_enable': "16",
            'sync_journal': "0"
        }

        MDT_DEFAULTS = {
            'hsm_control': 'disabled'
        }

        parts = path.split("/")[1:]
        if parts[3] == 'lov':
            # /proc/fs/lustre/lov/testfs-MDT0000-mdtlov/stripesize
            mdt_name = parts[4].rsplit("-", 1)[0]
            conf_param = "%s.lov.%s" % (mdt_name, parts[5])
            try:
                return configs[conf_param]
            except KeyError:
                return LOV_DEFAULTS[parts[5]]
        elif parts[3] == 'obdfilter':
            # /proc/fs/lustre/obdfilter/testfs-OST0000/writethrough_cache_enable
            conf_param = "%s.ost.%s" % (parts[4], parts[5])
            try:
                return configs[conf_param]
            except KeyError:
                return OBDFILTER_DEFAULTS[parts[5]]
        elif parts[3] == 'mdt':
            # /proc/fs/lustre/mdt/testfs-MDT0000/hsm_control
            mdt_name = parts[4]
            conf_param = "%s.mdt.%s" % (mdt_name, parts[5])
            try:
                print configs
                return configs[conf_param]
            except KeyError:
                return MDT_DEFAULTS[parts[5]]

        raise NotImplementedError("Simulator cannot resolve '%s' to conf param name" % path)

    def detect_scan(self, target_devices):
        local_targets = []
        mgs_target = None
        for serial, target in self._devices.state['targets'].items():
            log.info("targets: %s: %s %s" % (serial, target['label'], target['uuid']))
        for ha_label, resource in self._cluster.state['resources'].items():
            log.info("cluster: %s %s %s" % (ha_label, resource['uuid'], resource['device_path']))

        for target_device in target_devices:
            path = target_device['path']

            try:
                target = self._devices.get_target_by_path(self.fqdn, path)
            except KeyError:
                # Key error means this is not a target
                continue

            try:
                ha_resource = self._cluster.get_by_uuid(target['uuid'])
            except KeyError:
                log.warning("No HA resource for target %s/%s" % (target['label'], target['uuid']))
                continue
            location = self._cluster.resource_locations()[ha_resource['ha_label']]
            mounted = location == self.nodename
            local_targets.append({"name": target['label'],
                                  "uuid": target['uuid'],
                                  "params": {},
                                  "device_paths": [path],
                                  "mounted": mounted})

            if target['label'] == 'MGS':
                mgs_target = target

        mgs_targets = defaultdict(lambda: [])
        if mgs_target is not None:
            for target_label in self._devices.mgt_get_target_labels(mgs_target['mgsnode']):
                target = self._devices.get_target_by_label(target_label)

                mgs_targets[target['fsname']].append({
                    'uuid': target['uuid'],
                    'name': target['label'],
                    'nid': target['primary_nid']
                })

        result = {"local_targets": local_targets,
                  "mgs_targets": mgs_targets,
                  "mgs_conf_params": {}}
        log.debug("detect_scan: %s" % json.dumps(result, indent = 2))

        return result

    def read_proc(self, path):
        target = self._proc_path_to_target(path)
        configs = self._devices.mgt_get_conf_params(target['mgsnode'])
        return self._proc_path_to_conf_param(configs, path)

    def set_conf_param(self, key, value):
        mgt = None
        for target in self._targets_started_here:
            if target['label'] == 'MGS':
                mgt = target
                break
        if mgt is None:
            raise RuntimeError("Tried to run set_conf_param but not target named MGS is started on %s" % self.fqdn)

        self._devices.mgt_set_conf_param(mgt['mgsnode'], key, value)

        if 'hsm_control' in key:
            # e.g. testfs-MDT0000.mdt.hsm_control
            target = key.split('.')[0]
            fsname = target[:target.rfind('-')]
            self._simulator.control_hsm_coordinator(fsname, value)

    @property
    def filename(self):
        return "fake_server_%s.json" % self.fqdn

    @property
    def has_power(self):
        return self._simulator.power.server_has_power(self.fqdn)

    @property
    def registered(self):
        try:
            return self.crypto.certificate_file is not None
        except AttributeError:
            return False

    @property
    def agent_is_running(self):
        with self._lock:
            if self._agent_client:
                return not self._agent_client.stopped.is_set()
            else:
                return False

    @property
    def starting_up(self):
        with self._lock:
            return self.state['starting_up']

    @property
    def shutting_down(self):
        with self._lock:
            return self.state['shutting_down']

    @property
    def running(self):
        return self.starting_up or self.shutting_down or self.agent_is_running

    def join(self):
        with self._lock:
            if self._agent_client:
                self._agent_client.join()
                self._agent_client.reader.join()

    def stop(self):
        if self._agent_client:
            self._agent_client.stop()

    def shutdown_agent(self):
        if not self._agent_client:
            # Already stopped?
            return

        with self._lock:
            self._agent_client.stop()
            self._agent_client.join()
            # Have to join the reader explicitly, normal AgentClient code
            # skips it because it's slow to join (waits for long-polling GET
            # to complete)
            self._agent_client.reader.join()

            self._agent_client = None

    def start_agent(self):
        with self._lock:
            self._agent_client = AgentClient(
                url = self._simulator.url + "message/",
                action_plugins = FakeActionPlugins(self, self._simulator),
                device_plugins = FakeDevicePlugins(self),
                server_properties = self,
                crypto = self.crypto)
            self._agent_client.start()

    def _enter_shutdown(self):
        with self._lock:
            self.state['shutting_down'] = True
            self.save()

    def _exit_shutdown(self):
        with self._lock:
            self.state['shutting_down'] = False
            self.save()

    def shutdown(self, simulate_shutdown = False, reboot = False):
        """
        Shutdown the simulated server.
        :param simulate_shutdown: Simulate a server shutdown, delays and all.
        :param reboot: Restart the server after shutdown completes.
        """
        def blocking_shutdown():
            log.info("%s beginning shutdown" % self.fqdn)
            self._enter_shutdown()

            shutdown_start_time = IMLDateTime.utcnow()
            self.shutdown_agent()
            self._cluster.leave(self.nodename)
            shutdown_end_time = IMLDateTime.utcnow()

            shutdown_time = (shutdown_end_time - shutdown_start_time).seconds
            while shutdown_time < MIN_SHUTDOWN_DURATION:
                if not simulate_shutdown:
                    break

                remaining_delay = MIN_SHUTDOWN_DURATION - shutdown_time
                log.info("%s, sleeping for %d seconds on shutdown" % (self.fqdn, remaining_delay))

                shutdown_time += remaining_delay
                time.sleep(remaining_delay)

            self._exit_shutdown()
            log.info("%s shutdown complete" % self.fqdn)

            if reboot:
                log.info("%s rebooting" % self.fqdn)
                self.startup(simulate_shutdown)

        class NonBlockingShutdown(threading.Thread):
            def run(self):
                try:
                    blocking_shutdown()
                except IOError:
                    # Sometimes the cluster state dir gets nuked from under
                    # the thread that's shutting down, which is OK. If there
                    # are truly IOErrors to worry about, they'll show up
                    # elsewhere.
                    pass

        if simulate_shutdown:
            NonBlockingShutdown().start()
        else:
            blocking_shutdown()

    def _enter_startup(self):
        with self._lock:
            self.state['starting_up'] = True
            self.save()

    def _exit_startup(self):
        with self._lock:
            self.state['starting_up'] = False
            self.save()

    def startup(self, simulate_bootup = False):
        """
        Start the simulated server.
        :param simulate_bootup: Simulate a server bootup, delays and all.
        """
        if not 'worker' in self.fqdn and not self.has_power:
            log.warning("%s can't start; no PSUs have power" % self.fqdn)
            return
        if not self.registered:
            log.warning("%s can't start; not registered" % self.fqdn)
            return
        if self.running and not self.shutting_down:
            log.warning("%s already running; not starting again" % self.fqdn)
            return

        def blocking_startup():
            log.info("%s beginning startup" % self.fqdn)

            startup_time = 0
            # Mixing shutdown/startup state here is a little weird, but
            # this only happens when it's explicitly requested by a caller
            # that wants full server simulation. The end result is that
            # simulating a reboot is easier if we deal with waiting for
            # the shutdown to finish here before moving on to startup.
            while simulate_bootup and self.shutting_down:
                log.info("%s, waiting for shutdown (%d)" % (self.fqdn, startup_time))
                startup_time += 1
                time.sleep(1)

            # This may happen to the losing thread(s) during startup after
            # a multi-PDU power cycle.
            if self.starting_up:
                log.info("%s exiting startup because another thread is already doing it?" % self.fqdn)
                return

            self._enter_startup()
            self.boot_time = IMLDateTime.utcnow()

            while startup_time < MIN_STARTUP_DURATION:
                if not simulate_bootup:
                    break

                remaining_delay = MIN_STARTUP_DURATION - startup_time
                log.info("%s, sleeping for %d seconds on boot" % (self.fqdn, remaining_delay))

                startup_time += remaining_delay
                time.sleep(remaining_delay)

            self.start_agent()
            self._cluster.join(self.nodename)

            self._exit_startup()
            log.info("%s startup complete" % self.fqdn)

        class NonBlockingStartup(threading.Thread):
            def run(self):
                blocking_startup()

        if simulate_bootup:
            NonBlockingStartup().start()
        else:
            blocking_startup()

    def reboot(self, simulate_reboot = False):
        if self.running:
            self.shutdown(simulate_reboot)

        self.startup(simulate_reboot)

    def start_corosync(self):
        with self._lock:
            self.state['corosync'].state = 'started'
            self.save()
            return agent_result_ok

    def start_corosync2(self):
        return self.start_corosync()

    def stop_corosync(self):
        with self._lock:
            self.state['corosync'].state = 'stopped'
            self.save()
            return agent_result_ok

    def stop_corosync2(self):
        return self.stop_corosync()

    def configure_network(self,
                          ring0_name, ring1_name=None,
                          ring0_ipaddr=None, ring0_prefix=None,
                          ring1_ipaddr=None, ring1_prefix=None):
        return agent_result_ok

    def configure_corosync(self,
                           ring0_name,
                           old_mcast_port,
                           new_mcast_port,
                           ring1_name=None,
                           ring0_ipaddr=None, ring0_prefix=None,
                           ring1_ipaddr=None, ring1_prefix=None):
        with self._lock:
            self.state['corosync'].mcast_port = new_mcast_port
            self.save()
            return agent_result_ok

    def configure_corosync2_stage_1(self, mcast_port, pcs_password):
        with self._lock:
            self.state['corosync'].mcast_port = mcast_port
            self.save()
            return agent_result_ok

    def configure_corosync2_stage_2(self, ring0_name, ring1_name, new_node_fqdn, create_cluster, mcast_port, pcs_password):
        return agent_result_ok

    def change_mcast_port(self, old_mcast_port, new_mcast_port):
        with self._lock:
            self.state['corosync'].mcast_port = new_mcast_port
            self.save()
            return agent_result_ok

    def get_corosync_autoconfig(self):
        with self._lock:
            port_names = {'tcp': 'eth', 'o2ib': 'ib'}
            inet4_addresses = []
            names = []

            for inet4_address in self.network_interfaces.keys():
                interface = self.network_interfaces[inet4_address]
                inet4_addresses.append(inet4_address)
                names.append('%s%s' % (port_names[interface['type']], interface['interface_no']))

            return agent_result({'interfaces': {names[0]: {'dedicated': False,
                                                           'ipaddr': inet4_addresses[0],
                                                           'prefix': 24},
                                                names[1]: {'dedicated': True,
                                                           'ipaddr': inet4_addresses[1],
                                                           'prefix': 24}},
                                 'mcast_port': self.state['corosync'].mcast_port})

    def start_pacemaker(self):
        with self._lock:
            self.state['pacemaker'].state = 'started'
            self.save()
            return agent_result_ok

    def stop_pacemaker(self):
        with self._lock:
            self.state['pacemaker'].state = 'stopped'
            self.save()
            return agent_result_ok

    def start_lnet(self):
        with self._lock:
            self.state['lnet_loaded'] = True
            self.state['lnet_up'] = True
            self.save()
            return agent_result_ok

    def stop_lnet(self):
        with self._lock:
            self.state['lnet_loaded'] = True
            self.state['lnet_up'] = False
            self.save()
            return agent_result_ok

    def unload_lnet(self):
        with self._lock:
            self.state['lnet_loaded'] = False
            self.state['lnet_up'] = False
            self.save()
            return agent_result_ok

    def load_lnet(self):
        with self._lock:
            self.state['lnet_loaded'] = True
            self.state['lnet_up'] = False
            self.save()
            return agent_result_ok

    def configure_lnet(self, **kwargs):
        with self._lock:
            lnet_configuration = kwargs['lnet_configuration']

            # First off destroy all the current nids
            for inet4_address in self.network_interfaces:
                self.network_interfaces[inet4_address]['lnd_network'] = None

            for nid in lnet_configuration['network_interfaces']:
                inet4_address = nid[0]
                self.network_interfaces[inet4_address]['lnd_type'] = nid[1]
                self.network_interfaces[inet4_address]['lnd_network'] = nid[2]

            self.state['network_interfaces'] = self.network_interfaces
            self.save()
            return agent_result_ok

    def unconfigure_lnet(self):
        # No with lock because configure_lnet does the with lock.
        self.configure_lnet(lnet_configuration = {'network_interfaces': [],
                                                  'state': 'lnet_unloaded'})
        return agent_result_ok

    def writeconf_target(self, writeconf=False, erase_params=False, device=None, mgsnode=None, failnode=None):
        if mgsnode is None:
            # When writeconfing an MGS, erase its simulated conf params
            target = self._devices.get_target_by_path(self.fqdn, device)
            self._devices.mgt_writeconf(target['mgsnode'])

    def check_block_device(self, device_type, path):
        serial = self._devices.get_by_path(self.fqdn, path)['serial_80']
        return self._devices.state['local_filesystems'].get(serial, None)

    def format_target(self, device_type, target_name, device, backfstype,
                      target_types=(), mgsnode=(), fsname=None,
                      failnode=(), servicenode=(), param={}, index=None,
                      comment=None, mountfsoptions=None, network=(),
                      device_size=None, mkfsoptions=None,
                      reformat=False, stripe_count_hint=None, iam_dir=False,
                      dryrun=False, verbose=False, quiet=False):

        # Remove warnings, but allow parameters to match real parameters.
        target_name, servicenode, param, comment, mountfsoptions, network, device_size, reformat, stripe_count_hint, iam_dir, dryrun, verbose, quiet, device_type

        def mgs_key(mgsnode):
            # Create a consistent mgs_key by sorting the nids
            return ":".join(sorted([",".join(sorted(mgsnids)) for mgsnids in mgsnode]))

        if 'mgs' in target_types:
            label = "MGS"
            mgsnode = tuple(self.nids)
            if failnode:
                mgsnode = tuple([mgsnode, tuple(failnode)])
            else:
                mgsnode = tuple([mgsnode])
            self._devices.mgt_create(mgs_key(mgsnode))
        elif 'mdt' in target_types:
            label = "%s-MDT%.4x" % (fsname, index)
        else:
            label = "%s-OST%.4x" % (fsname, index)

        tgt_uuid = uuid.uuid4().__str__()

        target = {
            'label': label,
            'uuid': tgt_uuid,
            'mgsnode': mgs_key(mgsnode),
            'fsname': fsname,
            'backfstype': backfstype,
            'index': index,
            'primary_nid': None
        }

        return self._devices.format(self.fqdn, device, mkfsoptions, target)

    def register_target(self, device_path, mount_point, backfstype):

        # FIXME: arbitrary choice of which NID to use, correctly this should be
        # whichever NID LNet uses to route to the MGS, or what is set
        # with servicenode.
        nid = self.nids[0]

        label = self._devices.register(self.fqdn, device_path, nid)

        return {'label': label}

    def open_firewall(self, port, address, proto, description, persist):
        return agent_result_ok

    def close_firewall(self, port, address, proto, description, persist):
        return agent_result_ok

    def configure_target_ha(self, primary, device, ha_label, uuid, mount_point):
        return agent_result(self._cluster.configure(self.nodename, device, ha_label, uuid, primary, mount_point))

    def unconfigure_target_ha(self, primary, ha_label, uuid):
        return agent_result(self._cluster.unconfigure(self.nodename, ha_label, primary))

    def purge_configuration(self, mgs_device_path, mgs_device_type, filesystem_name):
        serial = self._devices.get_by_path(self.fqdn, mgs_device_path)['serial_80']
        mgsnode = self._devices.state['targets'][serial]['mgsnode']
        self._devices.mgt_purge_fs(mgsnode, filesystem_name)

    def start_target(self, ha_label):
        resource = self._cluster.start(ha_label)
        return agent_result(resource['started_on'])

    def stop_target(self, ha_label):
        self._cluster.stop(ha_label)

        return agent_result_ok

    def import_target(self, device_type, path, pacemaker_ha_operation, validate_importable=False):
        return agent_result_ok

    def export_target(self, device_type, path):
        return agent_result_ok

    @property
    def _targets_started_here(self):
        uuid_started_on = {}

        for ha_label, resource in self._cluster.state['resources'].items():
            uuid_started_on[resource['uuid']] = resource['started_on']

        for (target, path) in self._devices.get_targets_by_server(self.fqdn):
            try:
                started_on = uuid_started_on[target['uuid']]
            except KeyError:
                # lustre target not known to cluster, not yet ha-configured
                # log.debug("Lustre target %s %s not known to cluster %s" % (target['label'], target['uuid'],
                #                                                            json.dumps(self._cluster.state['resources'], indent=2)))
                pass
            else:
                if started_on == self.nodename:
                    yield target

    def get_lustre_stats(self):
        result = {
            'target': {},
            'lnet': {},
            'jobid_var': 'procname_uid',
        }

        for target in self._targets_started_here:
            result['target'][target['label']] = self._devices.get_target_stats(target)
            # One coordinator per filesystem; just stick it on the first MDT
            if 'MDT0000' in target['label'] and target['fsname'] in self._simulator.coordinators:
                hsm_stats = self._simulator.coordinators[target['fsname']].hsm_stats
                result['target'][target['label']].update(hsm_stats)

        return result

    def get_node_stats(self):
        if not self.state['stats']:
            self.state['stats'] = {
                "hostname": self.fqdn,
                "meminfo": {
                    "SwapTotal": 1048568,
                    "SwapFree": 1048568,
                    "MemFree": 66196,
                    "HighTotal": 0,
                    "Committed_AS": 209916,
                    "NFS_Unstable": 0,
                    "VmallocChunk": 34359737507,
                    "Writeback": 0,
                    "MemTotal": 509856,
                    "VmallocUsed": 832,
                    "AnonPages": 32052,
                    "HugePages_Free": 0,
                    "Inactive": 195760,
                    "Active": 170680,
                    "CommitLimit": 1303496,
                    "Hugepagesize": 2048,
                    "Cached": 238156,
                    "SwapCached": 0,
                    "LowTotal": 509856,
                    "Dirty": 476,
                    "Mapped": 19916,
                    "HighFree": 0,
                    "VmallocTotal": 34359738367,
                    "Bounce": 0,
                    "HugePages_Rsvd": 0,
                    "PageTables": 5096,
                    "HugePages_Total": 0,
                    "Slab": 60816,
                    "Buffers": 96236,
                    "LowFree": 66196
                },
                "cpustats": {
                    "iowait": 58994,
                    "idle": 17632363,
                    "total": 17820617,
                    "user": 6160,
                    "system": 100260
                }
            }

        self.state['stats']['meminfo']['MemFree'] = utils.perturb(self.state['stats']['meminfo']['MemFree'], 5000, 0, self.state['stats']['meminfo']['MemTotal'])

        user_inc = random.randint(50, 100)
        idle_inc = random.randint(50, 100)
        self.state['stats']['cpustats']['user'] += user_inc
        self.state['stats']['cpustats']['idle'] += idle_inc
        self.state['stats']['cpustats']['total'] += (idle_inc + user_inc)
        # This is necessary to stop and start the simulator and avoid a big judder on the charts,
        # but in other circumstances it's a gratuitous amount of IO
        #self.save()

        return self.state['stats']
