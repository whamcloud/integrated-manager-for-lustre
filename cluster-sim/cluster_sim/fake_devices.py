#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from copy import deepcopy
import random
import threading
from cluster_sim.log import log

from cluster_sim.utils import Persisted, load_data, perturb


MDT_STAT_TEMPLATE = load_data('MDT_STAT_TEMPLATE.json')
OST_STAT_TEMPLATE = load_data('OST_STAT_TEMPLATE.json')


class FakeDevices(Persisted):
    """Represents shared storage, including all state which would live on a disk.  On initial
    setup this is just a set of imaginary volumes and device nodes, but when filesystems are
    formatted the Lustre state lives here too."""
    filename = 'devices.json'
    default_state = {
        'mgts': {},
        'targets': {},
        'devices': {},
        'presentations': {}
    }

    def __init__(self, path):
        super(FakeDevices, self).__init__(path)
        self._lock = threading.Lock()

    def setup(self, volume_count):
        for n in range(0, volume_count):
            self._add_lun()

    @property
    def serials(self):
        return self.state['devices'].keys()

    def get_device(self, serial):
        return self.state['devices'][serial]

    def _add_lun(self):
        n = len(self.state['devices'])
        serial = "FAKEDEVICE%.3d" % n
        major_minor = "%d:%d" % (n % 0xff00 >> 8, n % 0xff)
        self.state['devices'][serial] = {
            "major_minor": major_minor,
            "parent": None,
            "serial_83": serial,
            "serial_80": serial,
            "size": 1024 * 1024 * 1024 * 1024 * 32
        }

        return serial

    def _add_presentation(self, fqdn, serial):
            if not fqdn in self.state['presentations']:
                self.state['presentations'][fqdn] = {}

            self.state['presentations'][fqdn]["/dev/disk/by-id/scsi-%s-scsi0-0-0" % serial] = serial

    def add_presented_luns(self, count, fqdns):
        with self._lock:
            serials = [self._add_lun() for _ in range(0, count)]
            for serial in serials:
                for fqdn in fqdns:
                    self._add_presentation(fqdn, serial)

            self.save()

            return serials

    def remove_presentations(self, fqdn):
        with self._lock:
            try:
                del self.state['presentations'][fqdn]
            except KeyError:
                pass

    def format(self, fqdn, path, target_data):
        with self._lock:
            serial = self.get_by_path(fqdn, path)['serial_80']

            log.info("format: %s" % serial)
            self.state['targets'][serial] = target_data
            self.save()

    def register(self, fqdn, path, nid):
        with self._lock:
            serial = self.get_by_path(fqdn, path)['serial_80']
            target = self.state['targets'][serial]

            self.state['targets'][serial]['primary_nid'] = nid
            self.state['mgts'][target['mgsnode']]['targets'][target['label']] = {}
            self.save()

            return target['label']

    def get_presentations_by_server(self, fqdn):
        if fqdn in self.state['presentations']:
            return self.state['presentations'][fqdn]
        else:
            return {}

    def get_presentations_by_serial(self, serial):
        result = []
        for fqdn, presos in self.state['presentations'].items():
            for path, serial in presos.items():
                if serial == serial:
                    result.append(fqdn)

        return result

    def get_by_path(self, fqdn, path):
        serial = self.state['presentations'][fqdn][path]
        return self.state['devices'][serial]

    def get_targets_by_server(self, fqdn):
        if fqdn not in self.state['presentations']:
            return []

        result = []
        for path, serial in self.state['presentations'][fqdn].items():
            try:
                result.append((self.state['targets'][serial], path))
            except KeyError:
                pass

        return result

    def get_nodes(self, fqdn):
        if fqdn not in self.state['presentations']:
            return {}

        nodes = {}
        for path, serial in self.state['presentations'][fqdn].items():
            device = deepcopy(self.state['devices'][serial])
            device['path'] = path
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

        # This is necessary to stop and start the simulator and avoid a big judder on the charts,
        # but in other circumstances it's a gratuitous amount of IO
        #self.save()

        return target['stats']

    def mgt_create(self, mgsnode):
        with self._lock:
            self.state['mgts'][mgsnode] = {
                'targets': {},
                'conf_params': {}
            }
            self.save()

    def mgt_purge_fs(self, mgsnode, filesystem_name):
        with self._lock:
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
        with self._lock:
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
        return self.state['mgts'][mgsspec]['conf_params']
