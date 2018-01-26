# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.
from collections import defaultdict

import os
import re
import errno
import json
from iml_common.filesystems.filesystem import FileSystem
from iml_common.blockdevices.blockdevice import BlockDevice
from iml_common.lib.util import human_to_bytes
from toolz.functoolz import pipe, curry
from toolz.curried import map as cmap, filter as cfilter
from collections import namedtuple

DeviceMaps = namedtuple('device_maps', 'block_devices zpools zfs props')

_data = {}

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


def aggregator_get():
    import requests_unixsocket

    session = requests_unixsocket.Session()
    resp = session.get('http+unix://%2Fvar%2Frun%2Fdevice-aggregator.sock')
    payload = resp.text
    print "status code: {}\nresponse: {}".format(resp.status_code, payload)

    global _data
    _data = json.loads(payload)


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
        'filesystem_usage': x.get('ID_FS_USAGE'),
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
        'dm_vg_size': x.get('IML_DM_VG_SIZE'),
        'md_uuid': x.get('MD_UUID'),
        'md_device_paths': x.get('IML_MD_DEVICES')
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


def get_host_devices(fqdn):
    global _data
    host_data = _data.pop(fqdn)

    devices = json.loads(host_data)

    return DeviceMaps(devices["blockDevices"],
                      devices["zpools"],
                      devices["zfs"],
                      devices["props"])


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


def parse_mdraid_devs(xs, node_block_devices, ndt):
    mds = {}

    for x in xs:
        mds[x['md_uuid']] = {'path': x['path'],
                             'block_device': x['major_minor'],
                             'drives': paths_to_major_minors(node_block_devices,
                                                             ndt,
                                                             x['md_device_paths'])}

        # Finally add these devices to the canonical path list.
        ndt.add_normalized_devices(filter(DISK_BY_ID_PATH.match, x['paths']),
                                   filter(DEV_PATH.match, x['paths']))
        ndt.add_normalized_devices(x['md_device_paths'], [x['path']])

    return ndt, mds


# fixme: too crude?
def local_fs_filter(x):
    if x['filesystem_usage'] == 'filesystem' and x['filesystem_type'] in ['ext2', 'ext3', 'ext4']:
        return True
    elif x['filesystem_usage'] == 'other' and x['filesystem_type'] == 'swap':
        return True
    return False


def parse_localfs_devs(xs, node_block_devices, ndt):
    return {path_to_major_minor(node_block_devices, ndt, x['path']): ["", x['filesystem_type']] for x in xs}


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

    (ndt, mds) = parse_mdraid_devs(filter(lambda x: x.get('md_uuid') is not None, xs),
                                   node_block_devices,
                                   ndt)

    local_fs = parse_localfs_devs(filter(local_fs_filter, xs),
                                  node_block_devices,
                                  ndt)

    return [vgs, lvs, mds, local_fs, block_device_nodes]


def parse_zpools(zpool_map, zfs_map, block_device_nodes):
    zpools = {}
    datasets = {}
    # fixme: get zvols from zfs_map using some identifier to discern from datasets

    for pool in zpool_map.values():
        name = pool['name']
        guid = pool['guid']

        # fixme: get sizes from device-scanner
        size = 0
        # todo: won't work until bindings output integrated with device scanner
        drive_mms = get_drives(pool, block_device_nodes)

        # get phys_path for each child device, this is brittle because by-label link is unreliable
        # zpool_disk_serials = [dev['serial_83'] for dev in block_device_nodes.values()
        #                       if '/dev/disk/by-label/%s' % name in dev['paths']]
        #
        # drive_mms = [dev['major_minor'] for dev in block_device_nodes.values()
        #              if dev['serial_83'] in zpool_disk_serials]
        # if dev['id_path'] == phys_path]
        # if dev['id_fs_label'] == name]

        # fixme: re-enable check when drive_mms is reliable
        # if not drive_mms:
        #     raise RuntimeWarning("Could not find major minors for zpool '%s'" % name)

        # check for guid in zfs_map (not ideal but keys currently not usable)
        # use name/path as key, uid not guaranteed to be unique between datasets on different zpools
        # Note: may be able to use nested dataset information from libzfs bindings instead of zfs_map lookup
        _datasets = {ds['name']: {"name": ds['name'],
                                  "path": ds['name'],
                                  "block_device": "zfsset:%s" % ds['name'],
                                  "uuid": ds['id'],  # fixme: this is not a uuid and could collide
                                  "size": 0,
                                  "drives": drive_mms} for ds in [x for x in zfs_map.values() if x['poolGuid'] == guid]}

        _devs = {}

        if _datasets == {}:
            # keys should include the pool uuid because names not necessarily unique
            major_minor = "zfspool:%s" % guid
            zpools[guid] = {"name": name,
                            "path": name,
                            "block_device": major_minor,
                            "uuid": guid,
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

    return [zpools, datasets, block_device_nodes]


# fixme: won't work until bindings output integrated with device scanner, types need validating
def get_drives(zpool, device_nodes):
    """ return a list of physical drive major-minors from aggregator zpool representation """
    paths = [child.Disk.path for child in zpool.vdev.Root.children if child.Disk.whole_disk]
    serials = {d['serial_83'] for d in device_nodes.values() if set(paths) & set(d['paths'])}
    mms = {d['major_minor'] for d in device_nodes.values()
           if (d['serial_83'] in serials) and (d['device_type'] == 'disk')}

    # return len(paths) == len(mms)
    return mms


def discover_zpools(all_devs):
    # identify imported pools that reside on drives this host can see by
    ## build list of mms for DEVTYPE=disk and matching ID_PATH
    ## or matching serial (create serial set by matching paths in pools against those in devs)
    #  retrieve pool and relevant datasets
    # verify this host doesn't have conflicting view of imported state
    # add pools to current state including zfspools zfsdatasets and devs values
    # mm for
    UNSUPPORTED_STATES = ['EXPORTED', 'UNAVAIL']

    device_nodes = all_devs['devs']

    def extract(acc, data):
        maps = json.loads(data)

        # verify pool is imported
        pools = {id: pool for id, pool in maps['zpools'].items()
                 if pool['state'] not in UNSUPPORTED_STATES
                 and get_drives(pool, device_nodes).intersection(set(device_nodes.keys()))}

        # verify we haven't already got a representation for this pool on any of the other hosts
        if any(id for id in pools.keys() if id in acc['zpools'].keys()):
            raise RuntimeError("duplicate active representations of zpool (remote)")

        acc['zpools'].update(pools)
        acc['zfs'].update({k: v for k, v in maps['zfs'].items() if v['poolGuid'] in pools.keys()})

        return acc

    other_zpools_zfs = reduce(extract, _data.values(), defaultdict(dict))

    # verify we haven't already got a representation for this pool locally
    if any(id for id, pool in all_devs['zpools'].items()
           if id in other_zpools_zfs['zpools'].keys() and pool['state'] not in UNSUPPORTED_STATES):
        raise RuntimeError("duplicate active representations of zpool (local)")

    out = parse_zpools(other_zpools_zfs['zpools'], other_zpools_zfs['zfs'], all_devs['devs'])

    all_devs['zpools'].update(out[0])
    all_devs['zfs'].update(out[1])
    all_devs['devs'].update(out[2])

    return all_devs
    # matching = [p for p in device_maps.zpools.values()
    #             if get_drive_serials(p, device_nodes).intersection({device_nodes.keys()})]
    # return matching


#  "drives": drive_mms} for ds in [x for x in zfs_map.values() if x['poolGuid']
#  == guid]}


def get_block_devices(fqdn):
    aggregator_get()

    device_maps = get_host_devices(fqdn)

    devs_list = parse_sys_block(device_maps.block_devices)
    devs_list.extend(parse_zpools(device_maps.zpools,
                                  device_maps.zfs,
                                  devs_list.pop(-1)))

    devs_dict = dict(zip(
        ['vgs', 'lvs', 'mds', 'local_fs', 'zfspools', 'zfsdatasets', 'devs'],
        devs_list))

    return discover_zpools(devs_dict)
    #
    # devs_list.extend(add_zpools(discovered_zpools))


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

    return pipe(device_paths,
                cmap(c_path_to_major_minor), cfilter(None), list)


@curry
def path_to_major_minor(node_block_devices, ndt, device_path):
    """ Return device major minor for a given device path """
    return node_block_devices.get(ndt.normalized_device_path(device_path))
