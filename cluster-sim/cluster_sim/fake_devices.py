#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import random

from cluster_sim.utils import Persisted, load_data, perturb


MDT_STAT_TEMPLATE = load_data('MDT_STAT_TEMPLATE.json')
OST_STAT_TEMPLATE = load_data('OST_STAT_TEMPLATE.json')


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

    def setup(self, volume_count):
        assert volume_count < 256
        for n in range(0, volume_count):
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
