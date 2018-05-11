# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.
import errno
import json
import os
import re
import socket
from collections import defaultdict
from collections import namedtuple

from toolz.curried import map as cmap, filter as cfilter
from toolz.functoolz import pipe, curry

from chroma_agent.lib.shell import AgentShell
from iml_common.blockdevices.blockdevice import BlockDevice

DeviceMaps = namedtuple('device_maps', 'block_devices zfspools')

# Python errno doesn't include this code
errno.NO_MEDIA_ERRNO = 123

DEV_PATH = re.compile('^/dev/[^/]+$')
DISK_BY_ID_PATH = re.compile('^/dev/disk/by-id/')
DISK_BY_PATH_PATH = re.compile('^/dev/disk/by-path/')
MAPPER_PATH = re.compile('^/dev/mapper/')


def scanner_cmd(cmd):
    # Because we are pulling from device-scanner,
    # It is very important that we wait for
    # the udev queue to settle before requesting new data
    AgentShell.run(["udevadm", "settle"])

    client = socket.socket(socket.AF_UNIX)
    client.settimeout(1)
    client.connect_ex("/var/run/device-scanner.sock")
    client.sendall(json.dumps(cmd) + "\n")

    out = ''

    while True:
        out += client.recv(1024)

        if out.endswith("\n"):

            try:
                return json.loads(out)
            except ValueError:
                pass


def get_default(prop, default_value, x):
    y = x.get(prop, default_value)
    return y if y is not None else default_value


def get_major_minor(x):
    return "%s:%s" % (x.get('major'), x.get('minor'))


def as_device(x):
    paths = get_default('paths', [], x)
    path = next(iter(paths), None)

    return {
        'major_minor': get_major_minor(x),
        'path': path,
        'paths': paths,
        'serial_80': x.get('scsi80'),
        'serial_83': x.get('scsi83'),
        'size': int(get_default('size', 0, x)),
        'filesystem_type': x.get('idFsType'),
        'filesystem_usage': x.get('idFsUsage'),
        'device_type': x.get('devType'),
        'device_path': x.get('devPath'),
        'partition_number': x.get('idPartEntryNumber'),
        'is_ro': x.get('isReadOnly'),
        'parent': None,
        'dm_multipath': x.get('dmMultipathDevicePath'),
        'dm_lv': x.get('dmLvName'),
        'dm_vg': x.get('dmVgName'),
        'lv_uuid': x.get('lvUuid'),
        'vg_uuid': x.get('vgUuid'),
        'dm_slave_mms': get_default('dmSlaveMms', [], x),
        'dm_vg_size': x.get('dmVgSize'),
        'md_uuid': x.get('mdUuid'),
        'md_device_paths': x.get('mdDevices'),
        'is_mpath': get_default('isMpath', False, x),
    }


def get_parent_path(p):
    return os.sep.join(p.split(os.sep)[0:-1])


def find_device_by_device_path(p, xs):
    return next((d for d in xs if d['device_path'] == p), None)


def mutate_parent_prop(xs):
    disks = [x for x in xs if x['device_type'] == 'disk']
    partitions = [x for x in xs if x['device_type'] == 'partition']

    for x in partitions:
        parent_path = get_parent_path(x['device_path'])
        device = find_device_by_device_path(parent_path, disks)

        if device:
            x['parent'] = device['major_minor']


def filter_device(x):
    # Exclude zero-sized devices
    if x['size'] == 0 or x['is_ro']:
        return False

    return True


def create_device_list(device_dict):
    return pipe(device_dict.itervalues(), cmap(as_device),
                cfilter(filter_device), list)


def lvm_populate(device):
    """ Create vg and lv entries for devices with dm attributes """
    vg_name, vg_size, lv_name, lv_uuid, vg_uuid, lv_size, lv_mm, lv_slave_mms = \
        map(device.get,
            ('dm_vg', 'dm_vg_size', 'dm_lv', 'lv_uuid', 'vg_uuid', 'size', 'major_minor', 'dm_slave_mms'))

    vg = {
        'name': vg_name,
        'uuid': vg_uuid,
        'size': int(vg_size),
        'pvs_major_minor': []
    }

    [
        vg['pvs_major_minor'].append(mm) for mm in lv_slave_mms
        if mm not in vg['pvs_major_minor']
    ]

    # Do this to cache the device, type see blockdevice and filesystem for info.
    BlockDevice('lvm_volume', '/dev/mapper/%s-%s' % (vg_name, lv_name))

    lv = {
        'name': lv_name,
        'uuid': lv_uuid,
        'size': lv_size,
        'block_device': lv_mm
    }

    return vg, lv


@curry
def link_dm_slaves(block_device_nodes, ndt, x):
    """ link dm slave devices back to the mapper devices using mm to look up path """
    for slave_mm in x.get('dm_slave_mms', []):
        ndt.add_normalized_devices(
            filter(DISK_BY_ID_PATH.match,
                   block_device_nodes[slave_mm]['paths']),
            filter(MAPPER_PATH.match, x.get('paths')))


def parse_dm_devs(xs, block_device_nodes, ndt):
    vgs = {}
    lvs = defaultdict(dict)

    results = [lvm_populate(x) for x in xs if x.get('dm_lv') is not None]

    for vg, lv in results:
        vgs[vg['name']] = vg
        lvs[vg['name']][lv['name']] = lv

    c_link_dm_slaves = link_dm_slaves(block_device_nodes, ndt)
    map(c_link_dm_slaves, filter(lambda x: x['is_mpath'], xs))

    return ndt, vgs, lvs


def parse_mdraid_devs(xs, node_block_devices, ndt):
    mds = {}

    for x in xs:
        mds[x['md_uuid']] = {
            'path':
            x['path'],
            'block_device':
            x['major_minor'],
            'drives':
            paths_to_major_minors(node_block_devices, ndt,
                                  x['md_device_paths'])
        }

        # Finally add these devices to the canonical path list.
        ndt.add_normalized_devices(
            filter(DISK_BY_ID_PATH.match, x['paths']),
            filter(DEV_PATH.match, x['paths']))

        ndt.add_normalized_devices(x['md_device_paths'], [x['path']])

    return ndt, mds


class NormalizedDeviceTable(object):
    table = {}

    def __init__(self, xs):
        map(self.build_normalized_table_from_device, xs)

    def build_normalized_table_from_device(self, x):
        paths = x['paths']

        dev_paths = filter(DEV_PATH.match, paths)
        disk_by_id_paths = filter(DISK_BY_ID_PATH.match, paths)
        disk_by_path_paths = filter(DISK_BY_PATH_PATH.match, paths)
        mapper_paths = filter(MAPPER_PATH.match, paths)

        self.add_normalized_devices(dev_paths, disk_by_path_paths)
        self.add_normalized_devices(dev_paths, disk_by_id_paths)
        self.add_normalized_devices(disk_by_path_paths, mapper_paths)
        self.add_normalized_devices(disk_by_id_paths, mapper_paths)

    def add_normalized_devices(self, xs, ys):
        for x in xs:
            for y in ys:
                self.add_normalized_device(x, y)

    def add_normalized_device(self, from_path, to_path):
        if from_path != to_path:
            self.table[from_path] = to_path

    def find_normalized_start(self, device_fullpath):
        '''
        :param device_fullpath: The device_path being search for
        :return: Given /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333
                returns
                /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333
                /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333-part1
                /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333-part9
                etc.
        '''

        return [
            value for value in self.table.values()
            if value.startswith(device_fullpath)
        ]

    def normalized_device_path(self, device_path):
        normalized_path = os.path.realpath(device_path)

        # This checks we have a completely normalized path, perhaps the
        # stack means our current normal path can actually be
        # normalized further.
        # So if the root to normalization takes multiple
        # steps this will deal with it
        # So if /dev/sdx normalizes to /dev/mmapper/special-device
        # and /dev/mmapper/special-device normalizes to /dev/md/mdraid1,
        # then /dev/sdx will normalize to /dev/md/mdraid1
        # /dev/sdx -> /dev/mmapper/special-device -> dev/md/mdraid1

        # As an additional measure to detect circular references
        # such as A->B->C->A in
        # this case we don't know which is the
        # normalized value so just drop out once
        # it repeats.
        visited = set()

        while (normalized_path not in visited) and (
                normalized_path in self.table):
            visited.add(normalized_path)
            normalized_path = self.table[normalized_path]

        return normalized_path


def parse_sys_block(device_map):
    xs = create_device_list(device_map['blockDevices'])

    mutate_parent_prop(xs)

    node_block_devices = reduce(
        lambda d, x: dict(d, **{x['path']: x['major_minor']}), xs, {})

    block_device_nodes = reduce(
        lambda d, x: dict(d, **{x['major_minor']: x}), xs, {})

    ndt = NormalizedDeviceTable(xs)

    (ndt, _, _) = parse_dm_devs(
        filter(lambda x: x.get('lv_uuid') is not None, xs), block_device_nodes,
        ndt)

    (ndt, _) = parse_mdraid_devs(
        filter(lambda x: x.get('md_uuid') is not None, xs), node_block_devices,
        ndt)

    return ndt


def get_normalized_device_table():
    """ process block device info returned by
        device-scanner to produce a ndt
    """
    return parse_sys_block(scanner_cmd("Stream"))


def parse_local_mounts(xs):
    """ process block device info returned by device-scanner to produce
        a legacy version of local mounts
    """
    return [
        (d['source'], d['target'], d['fstype'])
        for d in xs
    ]


def get_local_mounts():
    xs = scanner_cmd("Stream")['localMounts']
    return parse_local_mounts(xs)


def paths_to_major_minors(node_block_devices, ndt, device_paths):
    """
    Create a list of device major minors for a list of
    device paths from _path_to_major_minor dict.
    If any of the paths come back as None, continue to the next.

    :param node_block_devices: dict of major-minor ids keyed on path
    :param ndt: normalised device table
    :param device_paths: The list of paths to get
        the list of major minors for.
    :return: list of dev_major_minors, or an empty
        list if any device_path is not found.
    """
    c_path_to_major_minor = path_to_major_minor(node_block_devices, ndt)

    return pipe(device_paths, cmap(c_path_to_major_minor), cfilter(None), list)


@curry
def path_to_major_minor(node_block_devices, ndt, device_path):
    """ Return device major minor for a given device path """
    return node_block_devices.get(ndt.normalized_device_path(device_path))
