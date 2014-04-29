#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2014 Intel Corporation All Rights Reserved.
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


from copy import deepcopy
import random
import threading
import re
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
        'presentations': {},
        'local_filesystems': {}
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

    def format_local(self, fqdn, path, filesystem_type):
        """Format a local filesystem"""
        with self._lock:
            serial = self.get_by_path(fqdn, path)['serial_80']
            if serial in self.state['targets']:
                # This isn't actually illegal (if the Lustre target is offline, we could overwrite it), but
                # the code is simpler if we ban it for now.  If you need to do this then feel free to replace
                # this exception with some code to handle it.
                raise RuntimeError("Tried to format a local filesystem somewhere we already have a lustre target")

            self.state['local_filesystems'][serial] = filesystem_type

    def format(self, fqdn, path, mkfs_options, target_data):
        # defaults to what an OST would look like
        e2fs_dump = {
            'uuid': target_data['uuid'],
            'filesystem_type': "ext4",
            'inode_size': 256,
            'bytes_per_inode': 16384
        }
        # overrides for MDT
        if mkfs_options:
            for pattern in [r'-I\s*(?P<inode_size>\d+)', r'-i\s*(?P<bytes_per_inode>\d+)']:
                match = re.search(pattern, mkfs_options)
                if match:
                    for k, v in match.groupdict().items():
                        e2fs_dump[k] = int(v)

        """Format a Lustre target"""
        with self._lock:
            serial = self.get_by_path(fqdn, path)['serial_80']
            device = self.get_device(serial)
            e2fs_dump['inode_count'] = device['size'] / e2fs_dump['bytes_per_inode']

            log.info("format: %s" % serial)
            self.state['targets'][serial] = target_data
            self.save()

        return e2fs_dump

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

    def get_target_by_path(self, fqdn, path):
        serial = self.state['presentations'][fqdn][path]
        return self.state['targets'][serial]

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
            device['filesystem_type'] = self.state['local_filesystems'].get(serial, None)
            nodes[device['major_minor']] = device

        return nodes

    def get_target_stats(self, target):
        if not 'stats' in target:
            with self._lock:
                # Need to acquire lock because we are modifying structure of target
                # object which lives inside inside self._state

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
                target['stats']['client_count'] = perturb(target['stats']['client_count'], 1, 0, 100)
            target['stats']['filesfree'] = perturb(target['stats']['filesfree'], target['stats']['filestotal'] / 10, 0, target['stats']['filestotal'])
            target['stats']['kbytesfree'] = perturb(target['stats']['kbytesfree'], target['stats']['filestotal'] / 10, 0, target['stats']['kbytestotal'])
            for md_op in ['rmdir', 'close', 'open', 'unlink', 'rmdir', 'getxattr', 'mkdir']:
                target['stats']['stats'][md_op]['count'] += random.randint(0, 10000)
        elif 'OST' in target['label']:
            target['stats']['stats']['write_bytes']['sum'] += random.randint(0, 10000000000)
            target['stats']['stats']['read_bytes']['sum'] += random.randint(0, 10000000000)
            target['stats']['kbytesfree'] = perturb(target['stats']['kbytesfree'], target['stats']['kbytestotal'] / 10, 0, target['stats']['kbytestotal'])
            target['stats']['filesfree'] = perturb(target['stats']['filesfree'], target['stats']['filestotal'] / 10, 0, target['stats']['filestotal'])
            for stat in target['stats']['job_stats']:
                for key in ('read', 'write'):
                    stat[key]['sum'] += random.randint(0, 10 ** 9)
                for key in ('read', 'write', 'setattr', 'punch', 'sync'):
                    stat[key]['samples'] += random.randint(0, 100)

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

    def mgt_writeconf(self, mgsnode):
        with self._lock:
            self.state['mgts'][mgsnode]['conf_params'] = {}
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

    def get_target_by_label(self, label):
        for target in self.state['targets'].values():
            if target['label'] == label:
                return target

        raise KeyError(label)

    def get_conf_params_by_mgsspec(self, mgsspec):
        return self.conf_params_with_presentation(self.state['mgts'][mgsspec]['conf_params'])

    def mgt_get_conf_params(self, mgsnode):
        return self.conf_params_with_presentation(self.state['mgts'][mgsnode]['conf_params'])

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

    def conf_params_with_presentation(self, conf_params):
        # Add any additional presentation to the data that is
        # added by the system. /proc/ is a "special" file that
        # doesn't really have any contents itself, but is more
        # just a file interface into somewhere in the kernel.
        # As such, a retrieval from proc is actual code to
        # retrieve values, which may add presentation to the
        # original values we stored.
        for key, value in conf_params.iteritems():
            if key.endswith("llite.max_cached_mb"):
                # max_cached_mb now actually reports multiple stats in the one
                # file, need to specify a key for the actual max_cached_mb stat
                # to reflect the format of the real file.
                conf_params[key] = 'max_cached_mb: %s' % value

        return conf_params
