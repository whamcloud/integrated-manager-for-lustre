#
# INTEL CONFIDENTIAL
#
# Copyright 2013-2016 Intel Corporation All Rights Reserved.
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

from chroma_agent.lib.shell import AgentShell
from chroma_agent.device_plugins.linux_components.device_helper import DeviceHelper
import chroma_agent.lib.normalize_device_path as ndp
from chroma_agent.log import daemon_log

from chroma_agent.chroma_common.blockdevices.blockdevice import BlockDevice
from chroma_agent.chroma_common.blockdevices.blockdevice_zfs import ExportedZfsDevice
from chroma_agent.chroma_common.filesystems.filesystem import FileSystem
from chroma_agent.chroma_common.lib.exception_sandbox import exceptionSandBox


class ZfsDevices(DeviceHelper):
    """Reads zfs pools"""
    acceptable_health = ['ONLINE', 'DEGRADED']

    def __init__(self):
        self._zpools = {}

    @exceptionSandBox(daemon_log, [])
    def quick_scan(self):
        try:
            return AgentShell.try_run(['zfs', 'list', '-H', '-o', 'name,guid']).split("\n")
        except (IOError, OSError):
            return []

    @exceptionSandBox(daemon_log, None)
    def full_scan(self, block_devices):
        try:
            AgentShell.run(["partprobe"])    # Before looking for zfs pools, ensure we are relooked at the partitions, might throw errors so ignore return
            self._search_for_active(block_devices)
            self._search_for_inactive(block_devices)
        except OSError:                 # OSError occurs when ZFS is not installed.
            self._zpools = {}

    def _search_for_active(self, block_devices):
        # First look for active/imported zpools
        out = AgentShell.try_run(["zpool", "list", "-H", "-o", "name,size,guid,health"])

        for line in filter(None, out.split('\n')):
            self._add_zfs_pool(line, block_devices)

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
            out = AgentShell.try_run(["zpool", "import"])
        except AgentShell.CommandExecutionError as e:
            # zpool import errors with error code 1 if nothing available to import
            if e.result.rc == 1:
                out = ""
            else:
                raise e

        imports = {}
        pool_name = None

        for line in filter(None, out.split("\n")):
            match = re.match("(\s*)pool: (\S*)", line)
            if match:
                pool_name = match.group(2)

            match = re.match("(\s*)state: (\S*)", line)
            if match:
                if pool_name:
                    imports[pool_name] = match.group(2)
                    pool_name = None
                else:
                    daemon_log.warning("Found a zpool import state but had no pool_name")

        for pool, state in imports.iteritems():
            if state in self.acceptable_health:
                with ExportedZfsDevice(pool) as available:
                    if available:
                        out = AgentShell.try_run(["zpool", "list", "-H", "-o", "name,size,guid,health", pool])
                        self._add_zfs_pool(out, block_devices)
            else:
                daemon_log.warning("Not scanning zpool %s because it is %s." % (pool, state))

    def _add_zfs_pool(self, line, block_devices):
        pool, size_str, uuid, health = line.split()

        if health in self.acceptable_health:
            size = self._human_to_bytes(size_str)

            drive_mms = self._paths_to_major_minors(self._get_zpool_devices(pool))

            if drive_mms is None:
                daemon_log.warn("Could not find major minors for zpool '%s'" % pool)
                return

            # This will need discussion, but for now fabricate a major:minor. Do we ever use them as numbers?
            block_device = "zfspool:%s" % pool

            block_devices.block_device_nodes[block_device] = {'major_minor': block_device,
                                                              'path': pool,
                                                              'serial_80': None,
                                                              'serial_83': None,
                                                              'size': size,
                                                              'filesystem_type': None,
                                                              'parent': None}

            # Do this to cache the device, type see blockdevice and filesystem for info.
            BlockDevice('zfs', pool)
            FileSystem('zfs', pool)

            self._zpools[uuid] = {
                "name": pool,
                "path": pool,
                "block_device": block_device,
                "uuid": uuid,
                "size": size,
                "drives": drive_mms,
                "datasets": self._get_zpool_datasets(pool, drive_mms, block_devices),
                "zvols": self._get_zpool_zvols(pool, drive_mms, block_devices)
                }

    @property
    @exceptionSandBox(daemon_log, {})
    def zpools(self):
        return self._zpools

    @property
    @exceptionSandBox(daemon_log, {})
    def datasets(self):
        datasets = {}

        for pool_uuid, pool in self.zpools.items():
            datasets.update(pool["datasets"].items())

        return datasets

    @property
    @exceptionSandBox(daemon_log, {})
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
        out = AgentShell.try_run(['zpool', 'status', name])

        lines = [l for l in out.split("\n") if len(l) > 0]

        # Look title string above the info we want, this could clash but is unlikely.
        while (lines and re.match("(\s*)NAME(\s*)STATE(\s*)READ(\s*)WRITE(\s*)CKSUM", lines[0]) == None):
            lines[0:1] = []

        # Slice off the start and end bits we are not interested in.
        lines[0:2] = []
        lines[-1:] = []

        devices = []

        for line in lines:
            device = re.match("\s*(\S*)", line).group(1)
            devices += self.find_device_and_children(device)

        return devices

    def _get_zpool_datasets(self, pool_name, drives, block_devices):
        out = AgentShell.try_run(['zfs', 'list', '-H', '-o', 'name,avail,guid'])

        zpool_datasets = {}

        if out.strip() != "no datasets available":
            for line in filter(None, out.split('\n')):
                name, size_str, uuid = line.split()
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

                    # Do this to cache the device, type see blockdevice and filesystem for info.
                    BlockDevice('zfs', name)
                    FileSystem('zfs', name)

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

    def find_device_and_children(self, device):
        devices = []

        try:
            # Find the full path of the matching device for example, this ends
            # scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333 so find
            # /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333
            device = ndp.find_normalized_end(device)

            # Then find all the partitions for that disk and add them, they are all a child of this
            # zfs pool, so
            # scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333 includes
            # scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333-part1
            for device in ndp.find_normalized_start(device):
                daemon_log.debug("zfs device '%s'" % device)
                devices.append(device)
        except KeyError:
            pass

        return devices
