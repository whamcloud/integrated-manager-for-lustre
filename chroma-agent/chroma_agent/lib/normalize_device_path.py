# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import os
import glob
import re

MAPPERPATH = os.path.join('/dev', 'mapper')
DISKBYIDPATH = os.path.join('/dev', 'disk', 'by-id')

_NORMALIZE_DEVICE_TABLE = {}


def normalized_device_path(device_path):
    _prime_normalized_paths()

    normalized_path = os.path.realpath(device_path)

    # This checks we have a completely normalized path, perhaps the
    # stack means our current normal path can actually be normalized further.
    # So if the root to normalization takes multiple
    # steps this will deal with it
    # So if /dev/sdx normalizes to /dev/mmapper/special-device
    # and /dev/mmapper/special-device normalizes to /dev/md/mdraid1,
    # then /dev/sdx will normalize to /dev/md/mdraid1

    # As an additional measure to detect circular references
    # such as A->B->C->A in
    # this case we don't know which is the
    # normalized value so just drop out once
    # it repeats.
    visited = set()

    while (normalized_path not in visited) and (
            normalized_path in _NORMALIZE_DEVICE_TABLE):
        visited.add(normalized_path)
        normalized_path = _NORMALIZE_DEVICE_TABLE[normalized_path]

    return normalized_path


def find_normalized_start(device_fullpath):
    '''
    :param device_path: The device_path being search for
    :return: Given /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333
             returns
             /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333
             /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333-part1
             /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333-part9
             etc.
    '''

    _prime_normalized_paths()

    values = [
        value for value in _NORMALIZE_DEVICE_TABLE.values()
        if value.startswith(device_fullpath)
    ]

    return values


def _prime_normalized_paths():
    if _NORMALIZE_DEVICE_TABLE == {}:
        lookup_paths = ["%s/*" % DISKBYIDPATH, "%s/*" % MAPPERPATH]

        for path in lookup_paths:
            for f in glob.glob(path):
                add_normalized_device(os.path.realpath(f), f)

        try:
            root = re.search('root=([^ $\n]+)', open('/proc/cmdline').read())
        except IOError:
            root = None

        if root and os.path.exists(root.group(1)):
            add_normalized_device('/dev/root', root.group(1))


def add_normalized_device(path, normalized_path):
    '''
    Add an entry to the normalized path list, adding too often does no harm
    and adding something that is not completely canonical does no harm either,
    because the search routine is recursive so if
    A=>B and B=>C then A,B and C will all evaluate to the canonical value of C.

    This function does not add circular references, it is better to detect
    them in here than in the caller

    :param path: device path
    :param normalized_path: canonical path
    :return: No return value
    '''

    # Normalizing to itself makes no sense
    if path != normalized_path:
        _NORMALIZE_DEVICE_TABLE[path] = normalized_path
