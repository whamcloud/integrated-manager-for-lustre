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
from logging import DEBUG
from chroma_core.services import log_register

log = log_register('plugin_runner')
log.setLevel(DEBUG)

UNSUPPORTED_STATES = ['EXPORTED', 'UNAVAIL']

DeviceMaps = namedtuple('device_maps', 'block_devices zpools zfs props')

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

    return json.loads(payload)


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


def get_host_devices(fqdn, _data):
    try:
        host_data = _data.pop(fqdn)
    except KeyError:
        log.error('no aggregator data found for {}'.format(fqdn))
        raise

    devices = json.loads(host_data)

    try:
        device_maps = DeviceMaps(devices["blockDevices"],   # dict
                                 devices["zed"]["zpools"],  # dict
                                 devices["zed"]["zfs"],     # list
                                 devices["zed"]["props"])   # list
    except KeyError as e:
        log.error('badly formatted data found for {} : {} ({})'.format(fqdn, devices, e))
        raise

    return device_maps, _data


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
    """ map paths to major-minors but ignore paths that cannot be resolved (non-local) """
    items = pipe([(path_to_major_minor(node_block_devices, ndt, x['path']), ["", x['filesystem_type']]) for x in xs],
                 cfilter(lambda t: t[0] is not None),
                 list)
    return {t[0]: t[1] for t in items}


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


def parse_zpools(zpool_map, zfs_objs, block_device_nodes):
    """
    :param zpool_map: dictionary of pools keyed on guid
    :param zfs_objs: list of dataset dictionaries
    :param block_device_nodes: dictionary of block device dictionaries keyed on major minor
    :return: list of pools datasets and block_device_nodes
    """
    zpools = {}
    datasets = {}
    # fixme: get zvols from zfs_objs using some identifier to discern from datasets

    for pool in zpool_map.values():
        name = pool['name']
        guid = pool['guid']

        size = pool['size']
        drive_mms = get_drives([child['Disk'] for child in pool['vdev']['Root']['children']],
                               block_device_nodes)

        if not drive_mms:
            raise RuntimeWarning("Could not find major minors for zpool '%s'" % name)

        # todo: use name/path as key, uid not guaranteed to be unique between datasets on different zpools
        # Note: may be able to use nested dataset information from libzfs bindings instead of zfs_objs lookup
        def get_id(ds):
            return ds['poolGuid'] + '-' + ds['name']

        _datasets = {get_id(ds): {"name": ds['name'],
                                  "path": ds['name'],
                                  "block_device": "zfsset:{}".format(get_id(ds)),
                                  "uuid": get_id(ds),
                                  "size": 0,  # fixme
                                  "drives": drive_mms} for ds in [d for d in zfs_objs
                                                                  if int(d['poolGuid'], 16) == int(guid, 16)]}

        _devs = {}

        if _datasets == {}:
            # keys should include the pool uuid because names not necessarily unique
            major_minor = "zfspool:{}".format(guid)
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


def get_drives(pool_disks, device_nodes):
    """ return a list of physical drive major-minors from aggregator zpool representation """
    paths = [disk['path'] for disk in pool_disks if disk['whole_disk'] is True]

    serials = {d['serial_83'] for d in device_nodes.values() if set(paths) & set(d['paths'])}

    mms = {d['major_minor'] for d in device_nodes.values()
           if (d['serial_83'] in serials)}

    return mms


def discover_zpools(all_devs, _data):
    """
    Identify imported pools that reside on drives this host can see

    - gather information on pools active on other hosts
    - check the local host is reporting (can see) the underlying drives of said pool
    - verify the poor we want to add hasn't also been reported as active one another host
    - verify the localhost isn't also reporting the pool as active (it shouldn't be)
    - add pool and contained datasets to those to be reported to be connected to local host

    :return: the new dictionary of devices reported on the given host
    """
    def extract(acc, data):
        maps = json.loads(data)

        def match_drives(pool):
            pool_disks = [child['Disk'] for child in pool['vdev']['Root']['children']]

            return get_drives(pool_disks, all_devs['devs']).issubset(set(all_devs['devs'].keys()))

        try:
            # verify pool is imported
            pools = pipe(maps['zed']['zpools'].itervalues(),
                         cfilter(lambda pool: pool['state'] not in UNAVAILABLE_STATES),
                         cfilter(match_drives),
                         list)
        except KeyError as e:
            log.error('data not found, incorrect format %s [%s)' % (data, e))
            return acc

        pools = {pool['guid']: pool for pool in pools}

        # verify we haven't already got a representation for this pool on any of the other hosts
        if any(guid for guid in pools.keys() if guid in acc['zpools'].keys()):
            raise RuntimeError("duplicate active representations of zpool (remote)")

        acc['zpools'].update(pools)

        acc['zfs'].extend([d for d in maps['zed']['zfs']
                           if int(d['poolGuid'], 16) in [int(h, 16) for h in pools.keys()]])

        return acc

    other_zpools_zfs = reduce(extract, filter(None, _data.values()), {'zpools': {}, 'zfs': []})

    # verify we haven't already got a representation for this pool locally
    if any(guid for guid in all_devs['zfspools'].iterkeys()
           if guid in other_zpools_zfs['zpools'].keys()
            and other_zpools_zfs['zpools'][guid]['state'] not in UNSUPPORTED_STATES):
        raise RuntimeError("duplicate active representations of zpool (local)")

    # updates reported devices
    [all_devs[k].update(v) for k, v in zip(['zfspools', 'zfsdatasets', 'devs'],
                                           parse_zpools(other_zpools_zfs['zpools'],
                                                        other_zpools_zfs['zfs'],
                                                        all_devs['devs']))]

    del _data

    return all_devs


def get_block_devices(fqdn):
    _data = aggregator_get()

    try:
        log.debug('fetching devices for {}'.format(fqdn))
        device_maps, _data = get_host_devices(fqdn, _data)
    except Exception as e:
        log.error("iml-device-aggregator is not providing expected data, ensure "
                  "iml-device-scanner package is installed and relevant "
                  "services are running on storage servers (%s)" % e)
        return {}

    devs_list = parse_sys_block(device_maps.block_devices)
    devs_list.extend(parse_zpools(device_maps.zpools,
                                  device_maps.zfs,
                                  devs_list.pop(-1)))

    devs_dict = dict(zip(
        ['vgs', 'lvs', 'mds', 'local_fs', 'zfspools', 'zfsdatasets', 'devs'],
        devs_list))

    return discover_zpools(devs_dict, _data)


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
