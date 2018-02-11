# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.
from __future__ import print_function

import json

import os
import re
import glob
from toolz import partial, compose

import chroma_agent.lib.normalize_device_path as ndp
from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import daemon_log

from iml_common.blockdevices.blockdevice import BlockDevice
from iml_common.blockdevices.blockdevice_zfs import ZfsDevice, ZFS_OBJECT_STORE_PATH
from iml_common.filesystems.filesystem import FileSystem
from iml_common.lib.exception_sandbox import exceptionSandBox
from iml_common.lib import util

filter_empty = partial(filter, None)
strip_lines = partial(map, lambda x: x.strip())


def write_to_store(key, value):
    """
    :param key: key to update value for store
    :param value: value to assign to given key
    :param filepath: filepath of store
    :return: None
    """
    daemon_log.debug('write_to_store(): writing zfs data to %s. key: %s' % (ZFS_OBJECT_STORE_PATH, key))

    dataDict = read_store()

    # preserve other keys, only update the key specified
    dataDict[key] = value

    dataString = json.dumps(dataDict)

    with open(ZFS_OBJECT_STORE_PATH, 'w') as f:
        f.write(dataString)


def read_from_store(key):
    """ Read specific key from store """
    daemon_log.info('read_from_store(): reading zfs data from %s with key: %s' % (ZFS_OBJECT_STORE_PATH, key))

    return read_store()[key]


def find_name_in_store(pool_name):
    contents = read_store()

    try:
        next(pool for pool in contents.values() if pool['pool']['name'] == pool_name)
    except StopIteration:
        raise KeyError('No data for zpool %s found in store' % pool_name)


def read_store():
    """ Store file should always exist because it's created on agent initialisation """
    x = '{}'

    with open(ZFS_OBJECT_STORE_PATH, 'r') as f:
        y = f.read()

        if len(y) > len(x):
            x = y

    return json.loads(x)


def clean_list(xs):
    return filter_empty(strip_lines(xs))


def match_entry(x, name, exclude):
    """ identify config devices in any line listed in config not containing vdev keyword """
    return not any(substring in x for substring in (exclude + (name,)))


def _parse_line(xs):
    """ keywords in vdev config display for zpool that represent structure not an actual device """
    excluded = ('mirror', 'raidz', 'spare', 'cache', 'logs', 'NAME')

    # pair up keys with values found on the subsequent line
    zpool = dict(zip(xs[::2], xs[1::2]))

    zpool[u'devices'] = filter(lambda x: match_entry(x, zpool['pool'], excluded),
                               clean_list(zpool['config'].split('\n')))

    def kv_split(words):
        return {words[0]: (words[1] if len(words) > 1 else None)}

    zpool[u'devices'] = reduce(lambda d, x: d.update(kv_split(x.split())) or d,
                               zpool['devices'],
                               {})

    del (zpool['config'])
    return zpool


def get_zpools(active=True):
    """
    Parse shell output from 'zpool import' or 'zpool status' commands and return zpool details in list of dicts.
    Always return list and split output on keyword followed by colon but ignore urls.

    Command issued depends on both input arguments and is either of the form:

    # [root@lotus-33vm17 ~]# zpool import
    #    pool: lustre
    #      id: 5856902799170956568
    #   state: ONLINE
    #  action: The pool can be imported using its name or numeric identifier.
    #  config:
    #
    #  lustre  ONLINE
    #    sda  ONLINE
    #    sdb  ONLINE
    #
    #  ... (repeats for all discovered zpools)

    or:

    # [root@lotus-32vm5 ~]# zpool status
    #   pool: pool1
    #  state: ONLINE
    #   scan: none requested
    # config:
    #
    #         NAME   STATE     READ WRITE CKSUM
    #         pool1  ONLINE       0     0     0
    #           sdb  ONLINE       0     0     0
    #
    # errors: No known data errors
    #
    #  ... (repeats for all discovered zpools)

    :active: if True return details of imported zpools 'zpool status', otherwise return details of zpools
      available for import 'zpool import'
    :return: list of dicts with details of either imported or importable zpools
    """
    cmd_args = ['zpool', 'status' if (active is True) else 'import']
    out = AgentShell.try_run(cmd_args)

    if 'pool: ' not in out:
        return []

    transform_pools = compose(_parse_line,
                              lambda x: clean_list(re.split(r'\n\s*(\w+):\s', x)),
                              lambda x: '\npool: ' + x)

    return map(transform_pools, clean_list(re.split(r'pool:\s', out)))


def _get_zpool_datasets(pool_name, drives):
    """ Retrieve datasets belonging to a zpool """
    out = AgentShell.try_run(['zfs', 'list', '-H', '-o', 'name,avail,guid'])

    zpool_datasets = {}

    if out.strip() != "no datasets available":
        for line in filter(None, out.split('\n')):
            name, size_str, uuid = line.split()
            size = util.human_to_bytes(size_str)

            if name.startswith("%s/" % pool_name):
                # This will need discussion, but for now fabricate a major:minor. Do we ever use them as numbers?
                major_minor = "zfsset:%s" % uuid

                zpool_datasets[uuid] = {
                    "name": name,
                    "path": name,
                    "block_device": major_minor,
                    "uuid": uuid,
                    "size": size,
                    "drives": drives
                }

                daemon_log.debug("zfs mount '%s'" % name)

    return zpool_datasets


def _get_zpool_zvols(pool_name, drives, block_devices):
    """
    Each zfs pool may have zvol entries in it. This will parse those zvols and create
    device entries for them
    """
    zpool_vols = {}

    for zvol_path in glob.glob("/dev/%s/*" % pool_name):
        major_minor = block_devices.path_to_major_minor(zvol_path)

        if major_minor is None:
            continue

        uuid = zvol_path

        zpool_vols[uuid] = {
            "name": zvol_path,
            "path": zvol_path,
            "block_device": major_minor,
            "uuid": uuid,
            "size": block_devices.block_device_nodes[major_minor]["size"],
            "drives": drives
        }

        # Do this to cache the device, type see blockdevice and filesystem for info.
        BlockDevice('zfs', zvol_path)
        FileSystem('zfs', zvol_path)

    return zpool_vols


def find_device_and_children(device_path):
    devices = []

    try:
        # Then find all the partitions for that disk and add them, they are all a child of this
        # zfs pool, so
        # scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333 includes
        # scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333-part1
        for device in ndp.find_normalized_start(ndp.normalized_device_path(device_path)):
            daemon_log.debug("zfs device '%s'" % device)
            devices.append(device)
    except KeyError:
        pass

    return devices


def _list_zpool_devices(name, full_paths):
    """
    We are parsing either full vdev paths (including partitions):
    [root@node1 ~]# zpool list -PHv -o name lustre1
    lustre1
      /dev/disk/by-path/pci-0000:00:05.0-scsi-0:0:0:2-part1 9.94G 228K 9.94G - 0% 0%

    Or base devices:
    [root@node1 ~]# zpool list -PH -o name lustre1
    lustre1
      pci-0000:00:05.0-scsi-0:0:0:2 9.94G 228K 9.94G - 0% 0%

    :param name: zpool name to interrogate
    :param full_paths: True to retrieve full vdev paths (partitions), False for base device names
    :return: list of device paths or names sorted in descending order of string length
    """
    cmd_flags = '-%sHv' % ('P' if full_paths is True else '')
    out = AgentShell.try_run(['zpool', 'list', cmd_flags, '-o', 'name', name])

    # ignore the first (zpool name) and last (newline character)s line of command output
    return sorted([line.split()[0] for line in out.split('\n')[1:-1]], key=len, reverse=True)


def _get_all_zpool_devices(name):
    """
    Retrieve devices and children from base block devices used to create zpool

    Identify and remove partition suffix, we are only interested in the device

    :param name: zpool name
    :return: list of all devices related to the given zpool
    """
    fullpaths = _list_zpool_devices(name, True)

    devices = []
    for basename in _list_zpool_devices(name, False):
        fullpath = next(fullpath for fullpath in fullpaths if os.path.basename(fullpath).startswith(basename))
        device_path = os.path.join(os.path.dirname(fullpath), basename)
        devices.extend(find_device_and_children(device_path))
        fullpaths.remove(fullpath)

    return devices


def _populate_zpools():
    """
    Retrieve list of discovered ZfsPools, deal with race where pool is imported or exported
    between get_zpools() calls by filtering duplicates

    :return: set of ZfsPools which are either importable (inactive) or imported (active)
    """
    zpools = get_zpools()
    active_pool_names = [pool['pool'] for pool in zpools]
    zpools.extend(filter(lambda x: x['pool'] not in active_pool_names, get_zpools(active=False)))

    return zpools


class ZfsDevices(object):
    """Reads zfs pools"""
    acceptable_health = ['ONLINE', 'DEGRADED']

    def __init__(self):
        self._zpools = {}
        self._datasets = {}
        self._zvols = {}

    @exceptionSandBox(daemon_log, [])
    def quick_scan(self):
        try:
            return AgentShell.try_run(['zfs', 'list', '-H', '-o', 'name,guid']).split("\n")
        except (IOError, OSError):
            return []

    def _process_zpool(self, pool, block_devices):
        """
        Either read pool info from store if unavailable or inspect by importing

        :param pool: dict of pool info
        :return: None
        """
        pool_name = pool['pool']

        with ZfsDevice(pool_name, True) as zfs_device:

            if zfs_device.available:
                out = AgentShell.try_run(["zpool", "list", "-H", "-o", "name,size,guid", pool['pool']])
                self._add_zfs_pool(out, block_devices)
            else:
                # zpool probably imported elsewhere, attempt to read from store, this should return
                # previously seen zpool state either with or without datasets
                pool_id = pool.get('id', None)

                try:
                    if pool_id is None:
                        data = find_name_in_store(pool_name)
                    else:
                        data = read_from_store(pool_id)
                except KeyError as e:
                    daemon_log.error("ZfsPool unavailable and could not be retrieved from store: %s ("
                                     "pool info: %s)" % (e, pool))
                else:
                    # populate self._pools/datasets/zvols info from saved data read from store
                    self._update_pool_or_datasets(block_devices,
                                                  data['pool'],
                                                  data['datasets'],
                                                  data['zvols'])

    @exceptionSandBox(daemon_log, None)
    def full_scan(self, block_devices):
        try:
            [self._process_zpool(pool, block_devices) for pool in _populate_zpools()]
        except OSError:  # OSError occurs when ZFS is not installed.
            self._zpools = {}
            self._datasets = {}
            self._zvols = {}

    def _add_zfs_pool(self, line, block_devices):
        name, size_str, uuid = line.split()

        size = util.human_to_bytes(size_str)

        drive_mms = block_devices.paths_to_major_minors(_get_all_zpool_devices(name))

        if drive_mms is None:
            daemon_log.warning("Could not find major minors for zpool '%s'" % name)
            return

        datasets = _get_zpool_datasets(name, drive_mms)
        zvols = _get_zpool_zvols(name, drive_mms, block_devices)

        pool_md = {"name": name,
                   "path": name,
                   # fabricate a major:minor. Do we ever use them as numbers?
                   "block_device": "zfspool:%s" % name,
                   "uuid": uuid,
                   "size": size,
                   "drives": drive_mms}

        # write new data to store (_pool/datasets/Zvols)
        write_to_store(uuid, {'pool': pool_md, 'datasets': datasets, 'zvols': zvols})

        self._update_pool_or_datasets(block_devices, pool_md, datasets, zvols)

    def _update_pool_or_datasets(self, block_devices, pool, datasets, zvols):
        if (datasets == {}) and (zvols == {}):
            name = pool['name']
            block_devices.block_device_nodes[pool['block_device']] = {'major_minor': pool['block_device'],
                                                                      'path': name,
                                                                      'paths': [name],
                                                                      'serial_80': None,
                                                                      'serial_83': None,
                                                                      'size': pool['size'],
                                                                      'filesystem_type': None,
                                                                      'parent': None}

            # Do this to cache the device, type see blockdevice and filesystem for info.
            BlockDevice('zfs', name)
            FileSystem('zfs', name)

            self._zpools[pool['uuid']] = pool

        if datasets != {}:
            for info in datasets.itervalues():
                major_minor = info['block_device']
                name = info['name']
                block_devices.block_device_nodes[major_minor] = {'major_minor': major_minor,
                                                                 'path': name,
                                                                 'paths': [name],
                                                                 'serial_80': None,
                                                                 'serial_83': None,
                                                                 'size': info['size'],
                                                                 'filesystem_type': 'zfs',
                                                                 'parent': None}

                # Do this to cache the device, type see blockdevice and filesystem for info.
                BlockDevice('zfs', name)
                FileSystem('zfs', name)

            self._datasets.update(datasets)

        if zvols != {}:
            self._zvols.update(zvols)

    @property
    @exceptionSandBox(daemon_log, {})
    def zpools(self):
        return self._zpools

    @property
    @exceptionSandBox(daemon_log, {})
    def datasets(self):
        return self._datasets

    @property
    @exceptionSandBox(daemon_log, {})
    def zvols(self):
        return self._zvols
