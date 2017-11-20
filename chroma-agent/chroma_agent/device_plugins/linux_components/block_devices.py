# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.
from collections import defaultdict

import os
import re
import errno
import socket
import json
from chroma_agent.log import daemon_log
from iml_common.filesystems.filesystem import FileSystem
from iml_common.blockdevices.blockdevice import BlockDevice
from iml_common.lib.util import human_to_bytes
from chroma_agent.lib.shell import AgentShell
from toolz.functoolz import pipe, curry
from toolz.itertoolz import getter
from toolz.curried import map as cmap, filter as cfilter, mapcat as cmapcat
from collections import namedtuple

DeviceMaps = namedtuple('device_maps', 'block_devices zfspools')

# Python errno doesn't include this code
errno.NO_MEDIA_ERRNO = 123

DEV_PATH = re.compile('^/dev/[^/]+$')
DISK_BY_ID_PATH = re.compile('^/dev/disk/by-id/')
DISK_BY_PATH_PATH = re.compile('^/dev/disk/by-path/')
MAPPER_PATH = re.compile('^/dev/mapper/')

PRECEDENCE = [
    MAPPER_PATH, DISK_BY_ID_PATH, DISK_BY_PATH_PATH,
    re.compile('.+')
]


def get_idx(x):
    return [index for index, v in enumerate(PRECEDENCE) if v.match(x)][0]


def compare(x, y):
    idx1 = get_idx(x)
    idx2 = get_idx(y)

    if idx1 == idx2:
        return 0
    elif idx1 > idx2:
        return 1

    return -1


def sort_paths(xs):
    return sorted(xs, cmp=compare)


def scanner_cmd(cmd):
    client = socket.socket(socket.AF_UNIX)
    client.settimeout(1)
    client.connect_ex("/var/run/device-scanner.sock")
    client.sendall(json.dumps({"ACTION": cmd}))
    client.shutdown(socket.SHUT_WR)

    out = ''

    while True:
        data = client.recv(1024)
        size = len(data)

        if size == 0:
            break

        out += data

    return json.loads(out)


def get_default(prop, default_value, x):
    y = x.get(prop, default_value)
    return y if y is not None else default_value


def get_major_minor(x):
    return "%s:%s" % (x.get('MAJOR'), x.get('MINOR'))


def as_device(x):
    paths = sort_paths(get_default('PATHS', [], x))
    path = next(iter(paths), None)

    return {
        'major_minor': get_major_minor(x),
        'path': path,
        'paths': paths,
        'serial_80': x.get('IML_SCSI_80'),
        'serial_83': x.get('IML_SCSI_83'),
        'size': int(get_default('IML_SIZE', 0, x)) * 512,
        'filesystem_type': x.get('ID_FS_TYPE'),
        'device_type': x.get('DEVTYPE'),
        'device_path': x.get('DEVPATH'),
        'partition_number': x.get('ID_PART_ENTRY_NUMBER'),
        'is_ro': x.get('IML_IS_RO'),
        'parent': None,
        'dm_multipath': x.get('DM_MULTIPATH_DEVICE_PATH'),
        'dm_lv': x.get('DM_LV_NAME'),
        'dm_vg': x.get('DM_VG_NAME'),
        'dm_uuid': x.get('DM_UUID'),
        'dm_slave_mms': get_default('IML_DM_SLAVE_MMS', [], x),
        'dm_vg_size': x.get('IML_DM_VG_SIZE')
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


def fetch_device_maps():
    AgentShell.run(["udevadm", "settle"])
    info = scanner_cmd("info")

    return DeviceMaps(info["BLOCK_DEVICES"], info["ZFSPOOLS"])


def create_device_list(device_dict):
    return pipe(device_dict.itervalues(),
                cmap(as_device), cfilter(filter_device), list)


def parse_lvm_uuids(dm_uuid):
    """
    :param dm_uuid: device mapper uuid string (combined vg and lv with lvm prefix) from device_scanner
    :return: tuple of vg and lv UUIDs
    """
    lvm_pfix = 'LVM-'
    uuid_len = 32

    assert (dm_uuid.startswith(lvm_pfix) and len(dm_uuid) == (len(lvm_pfix) + (uuid_len * 2)))

    return dm_uuid[len(lvm_pfix):-uuid_len], dm_uuid[len(lvm_pfix) + uuid_len:]


def lvm_populate(device):
    """ Create vg and lv entries for devices with dm attributes """
    vg_name, vg_size, lv_name, dm_uuid, lv_size, lv_mm, lv_slave_mms = \
        map(device.get,
            ('dm_vg', 'dm_vg_size', 'dm_lv', 'dm_uuid', 'size', 'major_minor', 'dm_slave_mms'))

    vg_uuid, lv_uuid = parse_lvm_uuids(dm_uuid)

    vg = {'name': vg_name,
          'uuid': vg_uuid,
          'size': human_to_bytes(vg_size),
          'pvs_major_minor': []}

    [vg['pvs_major_minor'].append(mm) for mm in lv_slave_mms
     if mm not in vg['pvs_major_minor']]

    # Do this to cache the device, type see blockdevice and filesystem for info.
    BlockDevice('lvm_volume', '/dev/mapper/%s-%s' % (vg_name, lv_name))

    lv = {'name': lv_name,
          'uuid': lv_uuid,
          'size': lv_size,
          'block_device': lv_mm}

    return vg, lv


@curry
def link_dm_slaves(block_device_nodes, ndt, x):
    """ link dm slave devices back to the mapper devices using mm to look up path """
    for slave_mm in x.get('dm_slave_mms', []):
        ndt.add_normalized_devices(filter(DISK_BY_ID_PATH.match, block_device_nodes[slave_mm]['paths']),
                                   filter(MAPPER_PATH.match, x.get('paths')))


def parse_dm_devs(xs, block_device_nodes, ndt):
    vgs = {}
    lvs = defaultdict(dict)

    results = [lvm_populate(x) for x in xs if x.get('dm_lv') is not None]

    for vg, lv in results:
        vgs[vg['name']] = vg
        lvs[vg['name']][lv['name']] = lv

    c_link_dm_slaves = link_dm_slaves(block_device_nodes, ndt)
    map(c_link_dm_slaves, filter(lambda x: x['dm_uuid'].startswith('mpath-'), xs))

    return ndt, vgs, lvs


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
        :param device_path: The device_path being search for
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
    xs = create_device_list(device_map)

    mutate_parent_prop(xs)

    node_block_devices = reduce(
        lambda d, x: dict(d, **{x['path']: x['major_minor']}), xs, {})

    block_device_nodes = reduce(
        lambda d, x: dict(d, **{x['major_minor']: x}), xs, {})

    ndt = NormalizedDeviceTable(xs)

    (ndt, vgs, lvs) = parse_dm_devs(filter(lambda x: x.get('dm_uuid') is not None, xs),
                                    block_device_nodes,
                                    ndt)

    return block_device_nodes, node_block_devices, ndt, vgs, lvs


def parse_zpools(zpool_map, block_device_nodes):
    zpools = {}
    datasets = {}
    # fixme: get zvols from device-scanner
    zvols = {}

    for pool in zpool_map.values():
        # fixme: get sizes from device-scanner
        size = 0
        name = pool['NAME']
        uuid = pool['UID']

        drive_mms = [dev['major_minor'] for dev in block_device_nodes.values()
                     if '/dev/disk/by-label/%s' % name in dev['paths']]

        if not drive_mms:
            daemon_log.warning("Could not find major minors for zpool '%s'" % name)
            return

        # use name/path as key, uid not guaranteed to be unique between datasets on different zpools
        _datasets = {ds['DATASET_NAME']: {"name": ds['DATASET_NAME'],
                                          "path": ds['DATASET_NAME'],
                                          "block_device": "zfsset:%s" % ds['DATASET_NAME'],
                                          "uuid": ds['DATASET_UID'],
                                          "size": 0,
                                          "drives": drive_mms} for ds in pool['DATASETS'].values()}

        _devs = {}

        # normalized_table = block_devices.normalized_device_table
        # drive_mms = block_devices.paths_to_major_minors(_get_all_zpool_devices(name, normalized_table))
        # zvols = _get_zpool_zvols(name, drive_mms, block_devices)
        if _datasets == {}:
            # keys should include the pool uuid because names not necessarily unique
            major_minor = "zfspool:%s" % uuid
            zpools[uuid] = {"name": name,
                            "path": name,
                            "block_device": major_minor,
                            "uuid": uuid,
                            "size": size,
                            "drives": drive_mms}

            _devs[major_minor] = {'major_minor': major_minor,
                                  'path': name,
                                  'paths': [name],
                                  'serial_80': None,
                                  'serial_83': None,
                                  'size': size,
                                  'filesystem_type': None,
                                  'parent': None}

            # Do this to cache the device, type see blockdevice and filesystem for info.
            BlockDevice('zfs', name)
            FileSystem('zfs', name)

        else:
            datasets.update(_datasets)

            for info in _datasets.itervalues():
                major_minor = info['block_device']
                name = info['name']
                _devs[major_minor] = {'major_minor': major_minor,
                                      'path': name,
                                      'paths': [name],
                                      'serial_80': None,
                                      'serial_83': None,
                                      'size': 0,
                                      'filesystem_type': 'zfs',
                                      'parent': None}

                # Do this to cache the device, type see blockdevice and filesystem for info.
                BlockDevice('zfs', name)
                FileSystem('zfs', name)

        block_device_nodes.update(_devs)

    return zpools, datasets, zvols, block_device_nodes


class BlockDevices(object):
    MAPPERPATH = os.path.join('/dev', 'mapper')
    DISKBYIDPATH = os.path.join('/dev', 'disk', 'by-id')

    def __init__(self):
        device_maps = fetch_device_maps()

        (self.block_device_nodes, self.node_block_devices,
         self.normalized_device_table, self.vgs, self.lvs) = parse_sys_block(device_maps.block_devices)

        (self.zfspools, self.zfsdatasets, self.zfsvols, self.block_device_nodes) = parse_zpools(device_maps.zfspools,
                                                                                                self.block_device_nodes)

    def paths_to_major_minors(self, device_paths):
        """
        Create a list of device major minors for a list of
        device paths from _path_to_major_minor dict.
        If any of the paths come back as None, continue to the next.

        :param device_paths: The list of paths to get
            the list of major minors for.
        :return: list of dev_major_minors, or an empty
            list if any device_path is not found.
        """

        return pipe(device_paths,
                    cmap(self.path_to_major_minor), cfilter(None), list)

    def path_to_major_minor(self, device_path):
        """ Return device major minor for a given device path """
        return self.node_block_devices.get(
            self.normalized_device_table.normalized_device_path(device_path))

    def composite_device_list(self, source_devices):
        """
        This function takes a bunch of devices like MdRaid, EMCPower
        which are effectively composite devices made up
        from a collection of other devices and returns that
        list with the drives and everything nicely assembled.
        """
        devices = {}

        for device in source_devices:
            drive_mms = self.paths_to_major_minors(device['device_paths'])

            if drive_mms:
                devices[device['uuid']] = {
                    'path': device['path'],
                    'block_device': device['mm'],
                    'drives': drive_mms
                }

                # Finally add these devices to the canonical path list.
                for device_path in device['device_paths']:
                    self.normalized_device_table.add_normalized_device(
                        device_path, device['path'])

        return devices

    def find_block_devs(self, folder):
        # Map of major_minor to path
        # Should be able to look at the paths prop for all devs, and put
        # matching MM to path back in a list.

        def build_paths(x):
            return [(x['major_minor'], path) for path in x['paths']
                    if path.startswith(folder)]

        return pipe(self.block_device_nodes.itervalues(),
                    cmapcat(build_paths), dict)

    @classmethod
    def quick_scan(cls):
        return pipe(create_device_list(fetch_device_maps().block_devices),
                    cmapcat(getter("paths")), sorted) + fetch_device_maps().zfspools.keys()
