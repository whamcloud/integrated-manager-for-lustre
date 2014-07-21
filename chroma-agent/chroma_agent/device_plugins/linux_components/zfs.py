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

import re
import glob

from chroma_agent.chroma_common.lib import shell
from chroma_agent.device_plugins.linux_components.device_helper import DeviceHelper
import chroma_agent.lib.normalize_device_path as ndp
from chroma_agent.log import daemon_log


class ZfsDevices(DeviceHelper):
    """Reads zfs pools"""

    def __init__(self):
        self._zpools = {}

    def quick_scan(self):
        try:
            return shell.try_run(["zpool", "list", "-H", "-o", "name"]).split("\n")
        except (IOError, OSError):
            return []

    def full_scan(self, block_devices):
        try:
            self._search_for_active(block_devices)
            self._search_for_inactive(block_devices)
        except OSError:                 # OSError occurs when ZFS is not installed.
            self._zpools = {}

    def _search_for_active(self, block_devices):
        # First look for active/imported zpools
        out = shell.try_run(["zpool", "list", "-H", "-o", "name,size,guid"])

        lines = [l for l in out.split("\n") if len(l) > 0]

        for line in lines:
            pool, size_str, uuid = line.split()
            size = self._human_to_bytes(size_str)

            drives = [self._dev_major_minor(dp) for dp in self._get_zpool_devices(pool)]

            # This will need discussion, but for now fabricate a major:minor. Do we ever use them as numbers?
            block_device = "zfspool:%s" % pool

            block_devices.block_device_nodes[block_device] = {'major_minor': block_device,
                                                              'path': pool,
                                                              'serial_80': None,
                                                              'serial_83': None,
                                                              'size': size,
                                                              'filesystem_type': None,
                                                              'parent': None}

            self._zpools[uuid] = {
                "name": pool,
                "path": pool,
                "block_device": block_device,
                "uuid": uuid,
                "size": size,
                "drives": drives,
                "datasets": self._get_zpool_datasets(pool, drives, block_devices),
                "zvols": self._get_zpool_zvols(pool, drives, block_devices)
                }

    def _search_for_inactive(self, block_devices):
        # importable zpools
        # [root@lotus-33vm17 ~]# zpool import
        #    pool: lustre
        #      id: 5856902799170956568
        #   state: ONLINE
        #  action: The pool can be imported using its name or numeric identifier.
        #  config:
        #
        # 	lustre                             ONLINE
        # 	  scsi-0QEMU_QEMU_HARDDISK_disk15  ONLINE
        # 	  scsi-0QEMU_QEMU_HARDDISK_disk14  ONLINE
        try:
            out = shell.try_run(["zpool", "import"])
        except shell.CommandExecutionError as e:
            # zpool import errors with error code 1 if nothing available to import
            if e.rc == 1:
                out = ""
            else:
                raise e

        lines = [l for l in out.split("\n") if len(l) > 0]

        # Define them all to remove the warnings from Pyflakes
        pool = None
        uuid = None
        searching_config = False
        size = None
        state = None
        devices = []

        for line in lines:
            match = re.match("(\s*)pool: (\S*)", line)
            if match:
                # Are we moving to the next pool in the list?
                if pool:
                    self._add_zpool(pool, uuid, size, state, devices, block_devices)

                pool = match.group(2)
                uuid = None                 # Reset uuid so we throw errors if it is not found.
                searching_config = False
                size = 0
                state = None
                devices = []
                continue

            match = re.match("(\s*)id: (\S*)", line)
            if match:
                uuid = match.group(2)
                continue

            match = re.match("(\s*)state: (\S*)", line)
            if match:
                state = match.group(2)
                continue

            match = re.match("(\s*)action:", line)
            if match:
                continue

            match = re.match("(\s*)config:", line)
            if match:
                searching_config = True
                continue

            if searching_config:
                match = re.match("(\s*)%s" % pool, line)
                if match:
                    continue

                # Which means we are looking at devices
                match = re.match("(\s*)(\S*)(\s*)ONLINE", line)
                if match:
                    devices.append(ndp.find_normalized_end(match.group(2)))

        if pool:
            self._add_zpool(pool, uuid, size, state, devices, block_devices)

    def _add_zpool(self, pool, uuid, size, state, devices, block_devices):
        if state == "ONLINE":
            drives = [self._dev_major_minor(dp) for dp in devices]

            # This will need discussion, but for now fabricate a major:minor. Do we ever use them as numbers?
            block_device = "zfspool:%s" % pool

            block_devices.block_device_nodes[block_device] = {'major_minor': block_device,
                                                              'path': pool,
                                                              'serial_80': None,
                                                              'serial_83': None,
                                                              'size': size,
                                                              'filesystem_type': None,
                                                              'parent': None}

            self._zpools[uuid] = {
                "name": pool,
                "path": pool,
                "block_device": block_device,
                "uuid": uuid,
                "size": size,
                "drives": drives,
                "datasets": {},
                "zvols": {}
                }

    @property
    def zpools(self):
        return self._zpools

    @property
    def datasets(self):
        datasets = {}

        for pool_uuid, pool in self.zpools.items():
            datasets.update(pool["datasets"].items())

        return datasets

    @property
    def zvols(self):
        zvols = {}

        for pool_uuid, pool in self.zpools.items():
            zvols.update(pool["zvols"].items())

        return zvols

    def _get_zpool_devices(self, name):
        # TODO: Is there a better way of doing this
        # We are parsing something like this (with blank lines removed.)
        # [root@node1 ~]# zpool status lustre1
        #           pool: lustre1
        #  state: ONLINE But this can run to many lines
        #         of information.
        #   scan: none requested and so can
        #         this run to many lines.
        # config:
        # 	NAME          STATE     READ WRITE CKSUM
        # 	lustre1       ONLINE       0     0     0
        # 	  /tmp/zfsfs  ONLINE       0     0     0
        #
        # errors: No known data errors
        out = shell.try_run(['zpool', 'status', name])

        lines = [l for l in out.split("\n") if len(l) > 0]

        # Look title string above the info we want, this could clash but is unlikely.
        while (lines and re.match("(\s*)NAME(\s*)STATE(\s*)READ(\s*)WRITE(\s*)CKSUM", lines[0]) == None):
            lines[0:1] = []

        # Slice off the start and end bits we are not interested in.
        lines[0:2] = []
        lines[-1:] = []

        devices = []

        for line in lines:
            device = re.match("\t\s*(\S*)", line).group(1)
            device = ndp.find_normalized_end(device)
            daemon_log.debug("zfs device '%s'" % device)
            devices.append(device)

        return devices

    def _get_zpool_datasets(self, pool_name, drives, block_devices):
        out = shell.try_run(['zfs', 'list', '-o', 'name,guid,avail'])
        lines = [l for l in out.split("\n") if len(l) > 0]

        # Slice off the first line it is just titles.
        lines[0:1] = []

        zpool_datasets = {}

        for line in lines:
            name, uuid, size_str = line.split()
            size = self._human_to_bytes(size_str)

            if name.startswith("%s/" % pool_name):
                # This will need discussion, but for now fabricate a major:minor. Do we ever use them as numbers?
                major_minor = "zfsset:%s" % (len(self.datasets) + 1)
                block_devices.block_device_nodes[major_minor] = {'major_minor': major_minor,
                                                                  'path': name,
                                                                  'serial_80': None,
                                                                  'serial_83': None,
                                                                  'size': size,
                                                                  'filesystem_type': None,
                                                                  'parent': None}

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

    # Each zfs pool may have zvol entries in it. This will parse those zvols and create
    # device entries for them
    def _get_zpool_zvols(self, pool_name, drives, block_devices):
        zpool_vols = {}

        for zvol_path in glob.glob("/dev/%s/*" % pool_name):
            major_minor = self._dev_major_minor(zvol_path)
            uuid = zvol_path

            zpool_vols[uuid] = {
                "name": zvol_path,
                "path": zvol_path,
                "block_device": major_minor,
                "uuid": uuid,
                "size": block_devices.block_device_nodes[major_minor]["size"],
                "drives": drives
            }

        return zpool_vols
