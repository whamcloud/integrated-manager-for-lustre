# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.
from os import path

import chroma_agent.lib.normalize_device_path as ndp
from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import daemon_log

from iml_common.blockdevices.blockdevice import BlockDevice
from iml_common.blockdevices.blockdevice_zfs import ZfsDevice, get_zpools, ZFS_OBJECT_STORE_PATH, list_zpool_devices, \
    get_zpool_datasets, get_zpool_zvols
from iml_common.filesystems.filesystem import FileSystem
from iml_common.lib.exception_sandbox import exceptionSandBox
from iml_common.lib import util
from lib.util import read_from_store, write_to_store


def _find_device_and_children(device_path):
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


def _get_all_zpool_devices(name):
    """
    Retrieve devices and children from base block devices used to create zpool
    Identify and remove partition suffix, we are only interested in the device

    :param name: zpool name
    :return: list of all devices related to the given zpool
    """
    fullpaths = list_zpool_devices(name, True)
    devices = []

    for basename in list_zpool_devices(name, False):
        fullpath = next(fullpath for fullpath in fullpaths if path.basename(fullpath).startswith(basename))
        device_path = path.join(path.dirname(fullpath), basename)
        devices.extend(_find_device_and_children(device_path))
        fullpaths.remove(fullpath)

    return devices


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

    @exceptionSandBox(daemon_log, None)
    def full_scan(self, block_devices):
        zpools = []
        try:
            zpools.extend(get_zpools())
            active_pool_names = [pool['pool'] for pool in zpools]
            zpools.extend(filter(lambda x: x['pool'] not in active_pool_names, get_zpools(active=False)))

            for pool in zpools:
                with ZfsDevice(pool['pool'], True) as zfs_device:
                    if zfs_device.available:
                        out = AgentShell.try_run(["zpool", "list", "-H", "-o", "name,size,guid", pool['pool']])
                        self._add_zfs_pool(out, block_devices)
                    elif pool['state'] == 'UNAVAIL':
                        # zpool probably imported elsewhere, attempt to read from store, this should return
                        # previously seen zpool state either with or without datasets
                        try:
                            data = read_from_store(pool['id'], ZFS_OBJECT_STORE_PATH)
                        except KeyError as e:
                            daemon_log.warning("ZfsPool unavailable and could not be retrieved from store: %s ("
                                               "pool: %s)" % (e, pool['pool']))
                            continue
                        else:
                            # populate self._pools/datasets/zvols info from saved data read from store
                            self._update_pool_or_datasets(block_devices,
                                                          data['pool'],
                                                          data['datasets'],
                                                          data['zvols'])
                    else:
                        daemon_log.error("ZfsPool could not be accessed, reported info: %s" % pool)
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

        datasets = get_zpool_datasets(name, drive_mms)
        zvols = get_zpool_zvols(name, drive_mms, block_devices)

        pool_md = {"name": name,
                   "path": name,
                   # fabricate a major:minor. Do we ever use them as numbers?
                   "block_device": "zfspool:%s" % name,
                   "uuid": uuid,
                   "size": size,
                   "drives": drive_mms}

        # write new data to store (_pool/datasets/Zvols)
        daemon_log.debug('write_to_store(): writing data to %s. key: %s' % (ZFS_OBJECT_STORE_PATH, uuid))
        write_to_store(uuid, {'pool': pool_md, 'datasets': datasets, 'zvols': zvols}, ZFS_OBJECT_STORE_PATH)

        self._update_pool_or_datasets(block_devices, pool_md, datasets, zvols)

    def _update_pool_or_datasets(self, block_devices, pool, datasets, zvols):
        if (datasets == {}) and (zvols == {}):
            name = pool['name']
            block_devices.block_device_nodes[pool['block_device']] = {'major_minor': pool['block_device'],
                                                                      'path': name,
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
            for info in zvols.itervalues():
                name = info['name']

                # Do this to cache the device, type see blockdevice and filesystem for info.
                BlockDevice('zfs', name)
                FileSystem('zfs', name)

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
