# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import os
import re
import errno
import socket
import json
from itertools import chain, imap

import chroma_agent.lib.normalize_device_path as ndp

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


def flat_map(fn, xs):
    return chain.from_iterable(imap(fn, xs))


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


def getter(prop, default_value, x):
    y = x.get(prop, default_value)
    return y if y is not None else default_value


def get_major_minor(x):
    return "%s:%s" % (x.get('MAJOR'), x.get('MINOR'))


def as_device(x):
    paths = sort_paths(getter('PATHS', [], x))
    path = next(iter(paths), None)

    return {
        'major_minor': get_major_minor(x),
        'path': path,
        'paths': paths,
        'serial_80': x.get('IML_SCSI_80'),
        'serial_83': x.get('IML_SCSI_83'),
        'size': int(getter('IML_SIZE', 0, x)) * 512,
        'filesystem_type': x.get('ID_FS_TYPE'),
        'device_type': x.get('DEVTYPE'),
        'device_path': x.get('DEVPATH'),
        'partition_number': x.get('ID_PART_ENTRY_NUMBER'),
        'is_ro': x.get('IML_IS_RO'),
        'parent': None
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


def add_to_ndp(xs, ys):
    for x in xs:
        for y in ys:
            ndp.add_normalized_device(x, y)


def build_ndp_from_device(x):
    paths = x['paths']

    dev_paths = filter(DEV_PATH.match, paths)
    disk_by_id_paths = filter(DISK_BY_ID_PATH.match, paths)
    disk_by_path_paths = filter(DISK_BY_PATH_PATH.match, paths)
    mapper_paths = filter(MAPPER_PATH.match, paths)

    add_to_ndp(dev_paths, disk_by_path_paths)
    add_to_ndp(dev_paths, disk_by_id_paths)
    add_to_ndp(disk_by_path_paths, mapper_paths)
    add_to_ndp(disk_by_id_paths, mapper_paths)


class BlockDevices(object):
    MAPPERPATH = os.path.join('/dev', 'mapper')
    DISKBYIDPATH = os.path.join('/dev', 'disk', 'by-id')
    DISKBYPATHPATH = os.path.join('/dev', 'disk', 'by-path')
    SYSBLOCKPATH = os.path.join('/sys', 'block')
    MDRAIDPATH = os.path.join('/dev', 'md')

    def __init__(self):
        (self.block_device_nodes,
         self.node_block_devices) = self._parse_sys_block()

    def _parse_sys_block(self):
        info = scanner_cmd("info")

        xs = [as_device(x) for x in info.itervalues()]
        xs = filter(filter_device, xs)
        mutate_parent_prop(xs)

        node_block_devices = reduce(
            lambda d, x: dict(d, **{x['path']: x['major_minor']}), xs, {})

        block_device_nodes = reduce(
            lambda d, x: dict(d, **{x['major_minor']: x}), xs, {})

        map(build_ndp_from_device, xs)

        return (block_device_nodes, node_block_devices)

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
        device_mms = []
        for device_path in device_paths:
            device_mm = self.path_to_major_minor(device_path)

            if device_mm is None:
                continue

            device_mms.append(device_mm)
        return device_mms

    def path_to_major_minor(self, device_path):
        """ Return device major minor for a given device path """
        return self.node_block_devices.get(
            ndp.normalized_device_path(device_path))

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
                    'path': device["path"],
                    'block_device': device['mm'],
                    'drives': drive_mms
                }

                # Finally add these devices to the canonical path list.
                for device_path in device['device_paths']:
                    ndp.add_normalized_device(device_path, device['path'])

        return devices

    def find_block_devs(self, folder):
        # Map of major_minor to path
        result = {}
        # Should be able to look at the paths prop for all devs, and put
        # matching MM to path back in a list.

        xs = list(
            flat_map(lambda x: (x.paths, x.major_minor),
                     self.block_device_nodes))

        for x in xs:
            paths = x[0]
            mm = x[1]

            for path in paths:
                if path.startswith(folder):
                    result[mm] = path
                    break

        return result

    @classmethod
    def quick_scan(cls):
        """
            Return a very quick list of block devices from
            a number of sources so we can quickly see changes.
        """
        blocks = []

        for path in [
                cls.SYSBLOCKPATH, cls.MAPPERPATH, cls.DISKBYIDPATH,
                cls.DISKBYPATHPATH
        ]:
            blocks.extend(os.listdir(path))

        return blocks
