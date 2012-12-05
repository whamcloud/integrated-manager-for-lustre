#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import json
import logging
import random
import threading
import os
import datetime
import uuid
import time
from copy import deepcopy
from chroma_agent.device_plugins.jobs import ActionRunnerPlugin
from chroma_agent.plugin_manager import DevicePlugin


log = logging.getLogger(__name__)

if not log.handlers:
    handler = logging.FileHandler('cluster_sim.log')
    handler.setFormatter(logging.Formatter("[%(asctime)s: %(levelname)s/%(name)s] %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)


def load_data(filename):
    return json.loads(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename), 'r').read())

MDT_STAT_TEMPLATE = load_data('MDT_STAT_TEMPLATE.json')
OST_STAT_TEMPLATE = load_data('OST_STAT_TEMPLATE.json')


def perturb(value, max_perturb, min_bound, max_bound):
    perturbation = random.randint(0, max_perturb * 2) - max_perturb
    value += perturbation
    value = max(min_bound, value)
    value = min(max_bound, value)
    return value


class Persisted(object):
    filename = None
    default_state = {}

    def __init__(self, path):
        self.path = path

        self._file_lock = threading.Lock()
        try:
            self.state = json.load(open(os.path.join(self.path, self.filename), 'r'))
        except IOError:
            self.state = self.default_state

    def save(self):
        output_state = deepcopy(self.state)
        with self._file_lock:
            json.dump(output_state, open(os.path.join(self.path, self.filename), 'w'))


class FakeDevices(Persisted):
    """Simplified devices: everything is a SCSI drive visible to all hosts as the same
    node path on each host"""
    filename = 'devices.json'
    default_state = {
        'mgts': {},
        'targets': {},
        'devices': {}
    }

    def __init__(self, path):
        super(FakeDevices, self).__init__(path)

        if not self.state['devices']:
            #N = 64
            N = 10
            assert N < 256
            for n in range(0, N):
                serial = "FAKEDEVICE%.3d" % n
                major_minor = "253:%d" % n
                self.state['devices'][serial] = {
                    "major_minor": major_minor,
                    "parent": None,
                    "serial_83": serial,
                    "serial_80": serial,
                    "path": "/dev/disk/by-id/scsi-%s-scsi0-0-%d" % (serial, n),
                    "size": 1073741824
                }

            self.save()

    def mgt_create(self, mgsnode):
        self.state['mgts'][mgsnode] = {
            'targets': {},
            'conf_params': {}
        }
        self.save()

    def mgt_register_target(self, mgsnode, label):
        self.state['mgts'][mgsnode]['targets'][label] = {}
        self.save()

    def mgt_purge_fs(self, mgsnode, filesystem_name):
        targets_to_delete = []
        for target_label in self.state['mgts'][mgsnode]['targets'].keys():
            target = self.get_target_by_label(target_label)
            if target['fsname'] == filesystem_name:
                targets_to_delete.append(target_label)

        for target_label in targets_to_delete:
            del self.state['mgts'][mgsnode]['targets'][target_label]
        self.save()

    def mgt_get_target_labels(self, mgsnode):
        return self.state['mgts'][mgsnode]['targets'].keys()

    def mgt_get_conf_params(self, mgsnode):
        return self.state['mgts'][mgsnode]['conf_params']

    def mgt_set_conf_param(self, mgsnode, key, value):
        configs = self.state['mgts'][mgsnode]['conf_params']
        if value is None:
            try:
                del configs[key]
            except KeyError:
                pass
        else:
            configs[key] = value

        self.save()

    def get_target_by_label(self, label):
        for target in self.state['targets'].values():
            if target['label'] == label:
                return target

        raise KeyError(label)

    def get_conf_params_by_mgsspec(self, mgsspec):
        # mgsspec as defined in 'man mount.lustre'
        mgsnode = mgsspec.replace(":", ",")
        return self.state['mgts'][mgsnode]['conf_params']

    def get_by_path(self, path):
        for serial, device in self.state['devices'].items():
            if path == device['path']:
                return device
        raise ValueError()

    def get_nodes(self, fqdn):
        nodes = {}
        for device in self.state['devices'].values():
            nodes[device['major_minor']] = device
        return nodes

    def get_target_stats(self, target):
        if not 'stats' in target:
            # TODO: initialize filestotal and kbytestotal during format
            if 'MDT' in target['label']:
                target['stats'] = MDT_STAT_TEMPLATE
            elif 'OST' in target['label']:
                target['stats'] = OST_STAT_TEMPLATE
            elif target['label'] == 'MGS':
                target['stats'] = {}
            else:
                raise NotImplementedError(target['label'])

        if 'MDT' in target['label']:
            # Keep the client count mostly constant, blip it up or down once in a while
            if random.randint(0, 5) == 0:
                target['stats']['num_exports'] = perturb(target['stats']['num_exports'], 1, 0, 100)
            target['stats']['filesfree'] = perturb(target['stats']['filesfree'], target['stats']['filestotal'] / 10, 0, target['stats']['filestotal'])
            target['stats']['kbytesfree'] = perturb(target['stats']['kbytesfree'], target['stats']['filestotal'] / 10, 0, target['stats']['kbytestotal'])
            for md_op in ['rmdir', 'close', 'open', 'unlink', 'rmdir', 'getxattr', 'mkdir']:
                target['stats']['stats'][md_op]['count'] += random.randint(0, 10000)
        elif 'OST' in target['label']:
            target['stats']['stats']['write_bytes']['sum'] += random.randint(0, 10000000000)
            target['stats']['stats']['read_bytes']['sum'] += random.randint(0, 10000000000)
            target['stats']['kbytesfree'] = perturb(target['stats']['kbytesfree'], target['stats']['kbytestotal'] / 10, 0, target['stats']['kbytestotal'])
            target['stats']['filesfree'] = perturb(target['stats']['filesfree'], target['stats']['filestotal'] / 10, 0, target['stats']['filestotal'])

        self.save()

        return target['stats']


class FakeCluster(Persisted):
    filename = 'cluster.json'
    default_state = {
        'nodes': {},
        'resources': {}
    }

    def __init__(self, path):
        super(FakeCluster, self).__init__(path)
        self._lock = threading.Lock()

    def get_by_uuid(self, uuid):
        with self._lock:
            for ha_label, resource in self.state['resources'].items():
                if resource['uuid'] == uuid:
                    return resource

            raise KeyError(uuid)

    def clear_resources(self):
        with self._lock:
            self.state['resources'] = {}
            self.save()

    def resource_locations(self):
        with self._lock:
            locations = {}
            for ha_label, resource in self.state['resources'].items():
                locations[ha_label] = resource['started_on']

            return locations

    def get_running_resources(self, nodename):
        with self._lock:
            return [resource for resource in self.state['resources'].values() if resource['started_on'] == nodename]

    def start(self, ha_label):
        with self._lock:
            resource = self.state['resources'][ha_label]
            resource['started_on'] = resource['primary_node']
            log.debug("Starting resource %s on %s" % (ha_label, resource['primary_node']))
            self.save()
            return resource

    def stop(self, ha_label):
        with self._lock:
            resource = self.state['resources'][ha_label]
            resource['started_on'] = None
            self.save()
            return resource

    def failover(self, ha_label):
        with self._lock:
            resource = self.state['resources'][ha_label]
            resource['started_on'] = resource['secondary_node']
            self.save()
            return resource

    def failback(self, ha_label):
        with self._lock:
            resource = self.state['resources'][ha_label]
            resource['started_on'] = resource['primary_node']
            self.save()
            return resource

    def leave(self, nodename):
        with self._lock:
            log.debug("leave: %s" % nodename)
            for ha_label, resource in self.state['resources'].items():
                if resource['started_on'] == nodename:
                    options = set([resource['primary_node'], resource['secondary_node']]) - set([nodename])
                    if options:
                        destination = options.pop()
                        log.debug("migrating %s to %s" % (ha_label, destination))
                        resource['started_on'] = destination
                    else:
                        log.debug("stopping %s" % (ha_label))
                        resource['started_on'] = None

            self.save()

    def join(self, nodename):
        with self._lock:
            if not nodename in self.state['nodes']:
                self.state['nodes'][nodename] = {}

            for ha_label, resource in self.state['resources'].items():
                if resource['started_on'] is None:
                    if resource['primary_node'] == nodename:
                        log.debug("Starting %s on primary %s" % (ha_label, nodename))
                        resource['started_on'] = nodename
                    elif resource['secondary_node'] == nodename:
                        log.debug("Starting %s on secondary %s" % (ha_label, nodename))
                        resource['started_on'] = nodename
            self.save()

    def configure(self, nodename, device_path, ha_label, uuid, primary, mount_point):
        with self._lock:
            try:
                resource = self.state['resources'][ha_label]
            except KeyError:
                resource = {
                    'ha_label': ha_label,
                    'device_path': device_path,
                    'uuid': uuid,
                    'primary_node': None,
                    'secondary_node': None,
                    'mount_point': mount_point,
                    'started_on': None
                }

            if primary:
                resource['primary_node'] = nodename
            else:
                resource['secondary_node'] = nodename
            self.state['resources'][ha_label] = resource
            self.save()

    def unconfigure(self, nodename, ha_label, primary):
        with self._lock:
            try:
                resource = self.state['resource'][ha_label]
            except KeyError:
                return
            else:
                if primary:
                    del self.state['resource'][ha_label]
                else:
                    resource['secondary_node'] = None

                self.save()


class FakeClient(Persisted):
    default_state = {
        'mounts': []
    }

    def __init__(self, path, address, fake_devices, fake_cluster):
        self.address = address
        self._devices = fake_devices
        self._cluser = fake_cluster

        super(FakeClient, self).__init__(path)

    @property
    def filename(self):
        return "fake_client_%s.json" % self.address

    def mount(self, nids, filesystem_name):
        log.debug("FakeClient.mount %s %s" % (nids, filesystem_name))
        # Look up NIDs to an MGT
        # Check the MGT and targets are really started
        # Add an entry to self.state['mounts']
        if not (nids, filesystem_name) in self.state['mounts']:
            self.state['mounts'].append((nids, filesystem_name))
        self.save()

    def unmount(self, nids, filesystem_name):
        log.debug("FakeClient.unmount %s %s" % (nids, filesystem_name))
        if (nids, filesystem_name) in self.state['mounts']:
            self.state['mounts'].remove((nids, filesystem_name))
        self.save()

    def unmount_all(self):
        self.state['mounts'] = []
        self.save()

    def read_proc(self, path):
        # For each of our mounts, follow it back to an MGT
        # Resolve path to a conf param path

        LLITE_DEFAULTS = {
            'max_cached_mb': "32"
        }

        parts = path.split("/")[1:]
        if parts[3] == 'llite' and parts[4] == "*":
            # /proc/fs/lustre/llite/*/max_cached_mb
            if len(self.state['mounts']) > 1:
                # Assume caller is going to do a llite/*/ query expecting a single filesystem
                raise NotImplementedError("Multiple mounts on %s: %s" % (self.address, self.state['mounts']))

            if len(self.state['mounts']) == 0:
                raise RuntimeError("Tried to read proc on client %s but nothing is mounted" % self.address)

            mgsspec, fsname = self.state['mounts'][0]
            try:
                configs = self._devices.get_conf_params_by_mgsspec(mgsspec)
            except KeyError:
                print "mgsnode %s not found (known mgts are %s)" % (mgsspec, self._devices.state['mgts'].keys())
                raise KeyError("mgsnode %s not found (known mgts are %s)" % (mgsspec, self._devices.state['mgts'].keys()))
            try:
                return configs["%s.llite.%s" % (fsname, parts[5])]
            except KeyError:
                return LLITE_DEFAULTS[parts[5]]

        raise NotImplementedError("Couldn't resolve path %s on client %s" % (path, self.address))


class FakeServer(Persisted):
    default_state = {
        'lnet_loaded': False,
        'lnet_up': False,
        'stats': None
    }

    def __init__(self, path, fake_devices, fake_cluster, fqdn, nodename, nids):
        self.fqdn = fqdn
        self.nodename = nodename
        self.boot_time = datetime.datetime.utcnow()
        self.nids = nids

        self._log_messages = []
        self._devices = fake_devices
        self._cluster = fake_cluster

        self._cluster.join(nodename)

        super(FakeServer, self).__init__(path)

    def inject_log_message(self, message):
        log.debug("Injecting log message %s/%s" % (self.fqdn, message))
        self._log_messages.append({
                'source': 'cluster_sim',
                'severity': 1,
                'facility': 1,
                'message': message,
                'datetime': datetime.datetime.utcnow().isoformat() + 'Z'
            })

    def pop_log_messages(self):
        messages = self._log_messages
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

            raise RuntimeError("Cannot get proc information for %s, it's not started here (targets here are: %s)" % (
                mdt_name, [t['label'] for t in self._targets_started_here]))

        elif parts[3] == 'obdfilter':
            # /proc/fs/lustre/obdfilter/testfs-OST0000/writethrough_cache_enable
            ost_name = parts[4]
            for target in self._targets_started_here:
                if target['label'] == ost_name:
                    return target

            raise RuntimeError("Cannot get proc information for %s, it's not started here (targets here are: %s)" % (
                ost_name, [t['label'] for t in self._targets_started_here]))

        raise NotImplementedError("Simulator cannot resolve '%s' to target" % path)

    def _proc_path_to_conf_param(self, configs, path):
        """Resolve a /proc/foo/bar to a foo-MDT0000.bar.baz and look it up
        in the `configs` dict, or substitute a default if it's not set"""

        LOV_DEFAULTS = {
            'stripesize': "1"
        }

        OBDFILTER_DEFAULTS = {
            'writethrough_cache_enable': "0"
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
            ost_name = parts[4].rsplit("-", 1)[0]
            conf_param = "%s.obdfilter.%s" % (ost_name, parts[5])
            try:
                return configs[conf_param]
            except KeyError:
                return OBDFILTER_DEFAULTS[parts[5]]

        raise NotImplementedError("Simulator cannot resolve '%s' to conf param name" % path)

    def detect_scan(self):
        local_targets = []
        mgs_target = None
        for serial, target in self._devices.state['targets'].items():
            log.info("targets: %s: %s %s" % (serial, target['label'], target['uuid']))
        for ha_label, resource in self._cluster.state['resources'].items():
            log.info("cluster: %s %s %s" % (ha_label, resource['uuid'], resource['device_path']))
        for serial, target in self._devices.state['targets'].items():
            dev = self._devices.state['devices'][serial]['path']
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
                                  "devices": [dev],
                                  "mounted": mounted})

            if target['label'] == 'MGS':
                mgs_target = target

        mgs_targets = {}
        if mgs_target is not None:
            for target_label in self._devices.mgt_get_target_labels(mgs_target['mgsnode']):
                target = self._devices.get_target_by_label(target_label)
                if not target['fsname'] in mgs_targets:
                    mgs_targets[target['fsname']] = []
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

    @property
    def filename(self):
        return "fake_%s.json" % self.fqdn

    def start_lnet(self):
        self.state['lnet_loaded'] = True
        self.state['lnet_up'] = True
        self.save()

    def stop_lnet(self):
        self.state['lnet_loaded'] = True
        self.state['lnet_up'] = False
        self.save()

    def unload_lnet(self):
        self.state['lnet_loaded'] = False
        self.state['lnet_up'] = False
        self.save()

    def load_lnet(self):
        self.state['lnet_loaded'] = True
        self.state['lnet_up'] = False
        self.save()

    def format_target(self, device = None, target_types = None, mgsnode = None, fsname = None, failnode = None, reformat = None, mkfsoptions = None, index = None):
        if 'mgs' in target_types:
            label = "MGS"
            mgsnode = tuple(self.nids)
            if failnode:
                mgsnode = mgsnode + tuple(failnode)
            self._devices.mgt_create(",".join(mgsnode))
        elif 'mdt' in target_types:
            label = "%s-MDT%.4x" % (fsname, index)
        else:
            label = "%s-OST%.4x" % (fsname, index)

        tgt_uuid = uuid.uuid4().__str__()

        target = {
            'label': label,
            'uuid': tgt_uuid,
            'mgsnode': ",".join(mgsnode),
            'fsname': fsname,
            'index': index,
            'primary_nid': None
        }

        serial = self._devices.get_by_path(device)['serial_80']
        self._devices.state['targets'][serial] = target
        self._devices.save()

        return {
            'uuid': tgt_uuid,
            'inode_size': 512,
            'inode_count': 6666666
        }

    def register_target(self, device = None, mount_point = None):
        serial = self._devices.get_by_path(device)['serial_80']
        target = self._devices.state['targets'][serial]

        # FIXME: arbitrary choice of which NID to use, correctly this should be
        # whichever NID LNet uses to route to the MGS, or what is set
        # with servicenode.
        self._devices.state['targets'][serial]['primary_nid'] = self.nids[0]
        self._devices.save()

        self._devices.mgt_register_target(target['mgsnode'], target['label'])

        return {'label': target['label']}

    def configure_ha(self, device, ha_label, uuid, primary, mount_point):
        self._cluster.configure(self.nodename, device, ha_label, uuid, primary, mount_point)

    def unconfigure_ha(self, ha_label, uuid, primary):
        self._cluster.unconfigure(self.nodename, ha_label, primary)

    def purge_configuration(self, device, filesystem_name):
        serial = self._devices.get_by_path(device)['serial_80']
        mgsnode = self._devices.state['targets'][serial]['mgsnode']
        self._devices.mgt_purge_fs(mgsnode, filesystem_name)

    def start_target(self, ha_label):
        resource = self._cluster.start(ha_label)
        return {'location': resource['started_on']}

    def stop_target(self, ha_label):
        return self._cluster.stop(ha_label)

    @property
    def _targets_started_here(self):
        uuid_started_on = {}

        for ha_label, resource in self._cluster.state['resources'].items():
            uuid_started_on[resource['uuid']] = resource['started_on']

        for serial, target in self._devices.state['targets'].items():
            try:
                started_on = uuid_started_on[target['uuid']]
            except KeyError:
                # lustre target not known to cluster
                log.debug("Lustre target %s %s not known to cluster %s" % (target['label'], target['uuid'],
                                                                        json.dumps(self._cluster.state['resources'], indent=2)))
            else:
                if started_on == self.nodename:
                    yield self._devices.state['targets'][serial]

    def get_lustre_stats(self):
        result = {
            'target': {},
            'lnet': {}
        }

        for target in self._targets_started_here:
            result['target'][target['label']] = self._devices.get_target_stats(target)

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

        self.state['stats']['meminfo']['MemFree'] = perturb(self.state['stats']['meminfo']['MemFree'], 5000, 0, self.state['stats']['meminfo']['MemTotal'])

        user_inc = random.randint(50, 100)
        idle_inc = random.randint(50, 100)
        self.state['stats']['cpustats']['user'] += user_inc
        self.state['stats']['cpustats']['idle'] += idle_inc
        self.state['stats']['cpustats']['total'] += (idle_inc + user_inc)
        self.save()

        return self.state['stats']


class BaseFakeLinuxPlugin(DevicePlugin):
    _server = None

    def start_session(self):
        return {
            'mpath': {},
            'lvs': {},
            'devs': self._server._devices.get_nodes(self._server.fqdn),
            'local_fs': {},
            'mds': {},
            'vgs': {}
        }


class FakeLinuxNetworkPlugin(DevicePlugin):
    def start_session(self):
        return [{
            "tx_bytes": "24400222349",
            "name": "eth0",
            "rx_bytes": "1789870413"
        }]

    def update_session(self):
        return self.start_session()


class BaseFakeSyslogPlugin(DevicePlugin):
    _server = None

    def start_session(self):
        return {
            'messages': [
                {
                'source': 'cluster_sim',
                'severity': 1,
                'facility': 1,
                'message': "Lustre: Cluster simulator syslog session start %s %s" % (self._server.fqdn, datetime.datetime.now()),
                'datetime': datetime.datetime.utcnow().isoformat() + 'Z'
                }
            ]
        }

    def update_session(self):
        messages = self._server.pop_log_messages()
        if messages:
            self._server.log_messages = []
            return {
                'messages': messages
            }


class BaseFakeLustrePlugin(DevicePlugin):
    _server = None

    def start_session(self):
        if self._server.state['lnet_up']:
            nids = self._server.nids
        else:
            nids = None

        mounts = []
        for resource in self._server._cluster.get_running_resources(self._server.nodename):
            mounts.append({
                'device': resource['device_path'],
                'fs_uuid': resource['uuid'],
                'mount_point': resource['mount_point'],
                'recovery_status': {}
            })

        return {
            'resource_locations': self._server._cluster.resource_locations(),
            'lnet_loaded': self._server.state['lnet_loaded'],
            'lnet_nids': nids,
            'capabilities': ['manage_targets'],
            'metrics': {
                'raw': {
                    'node': self._server.get_node_stats(),
                    'lustre': self._server.get_lustre_stats()
                }
            },
            'mounts': mounts,
            'lnet_up': self._server.state['lnet_up'],
            'started_at': datetime.datetime.now().isoformat() + "Z",
            'agent_version': 'dummy'
        }

    def update_session(self):
        return self.start_session()


class FakeDevicePlugins():
    def __init__(self, server):
        self._server = server

        class FakeLinuxPlugin(BaseFakeLinuxPlugin):
            _server = self._server

        class FakeLustrePlugin(BaseFakeLustrePlugin):
            _server = self._server

        class FakeSyslogPlugin(BaseFakeSyslogPlugin):
            _server = self._server

        self._classes = {
            'linux': FakeLinuxPlugin,
            'linux_network': FakeLinuxNetworkPlugin,
            'lustre': FakeLustrePlugin,
            'jobs': ActionRunnerPlugin,
            'syslog': FakeSyslogPlugin
        }

    def get_plugins(self):
        return self._classes

    def get(self, name):
        return self._classes[name]


class FakeActionPlugins():
    def __init__(self, server, simulator):
        self._label_counter = 0
        self._server = server
        self._lock = threading.Lock()
        self._simulator = simulator

    @property
    def capabilities(self):
        return ['manage_targets']

    def run(self, cmd, kwargs):
        log.debug("FakeActionPlugins: %s %s" % (cmd, kwargs))
        with self._lock:
            if cmd == 'device_plugin':
                device_plugins = FakeDevicePlugins(self._server)
                if kwargs['plugin']:
                    return {kwargs['plugin']: device_plugins.get(kwargs['plugin'])(None).start_session()}
                else:
                    data = {}
                    for plugin, klass in device_plugins.get_plugins().items():
                        data[plugin] = klass(None).start_session()
                    return data

            elif cmd == 'configure_rsyslog':
                return
            elif cmd == 'configure_ntp':
                return
            elif cmd == 'deregister_server':
                sim = self._simulator
                server = self._server

                # This is going to try to join() me, so call it from a different thread
                class KillLater(threading.Thread):
                    def run(self):
                        # FIXME race, hoping that this is long enough for the job response
                        # to make it home
                        time.sleep(10)
                        server.crypto.delete()
                        sim.stop_server(server.fqdn)
                KillLater().start()

                return
            elif cmd == 'unconfigure_ntp':
                return
            elif cmd == 'unconfigure_rsyslog':
                return
            elif cmd == 'lnet_scan':
                if self._server.state['lnet_up']:
                    return self._server.nids
                else:
                    raise RuntimeError('LNet is not up')
            elif cmd == 'failover_target':
                return self._server._cluster.failover(kwargs['ha_label'])
            elif cmd == 'failback_target':
                log.debug(">>failback")
                rc = self._server._cluster.failback(kwargs['ha_label'])
                log.debug("<<failback %s" % rc)
                return rc
            elif cmd == 'writeconf_target':
                pass
            elif cmd == 'set_conf_param':
                self._server.set_conf_param(kwargs['key'], kwargs.get('value', None))
            else:
                try:
                    fn = getattr(self._server, cmd)
                except AttributeError:
                    raise RuntimeError("Unknown command %s" % cmd)
                else:
                    return fn(**kwargs)
