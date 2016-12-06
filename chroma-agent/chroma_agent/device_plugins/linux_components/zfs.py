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


import os
import re
import glob

from chroma_agent.lib.shell import AgentShell
import chroma_agent.lib.normalize_device_path as ndp
from chroma_agent.log import daemon_log

from chroma_agent.chroma_common.blockdevices.blockdevice import BlockDevice
from chroma_agent.chroma_common.blockdevices.blockdevice_zfs import ZfsDevice
from chroma_agent.chroma_common.filesystems.filesystem import FileSystem
from chroma_agent.chroma_common.lib.exception_sandbox import exceptionSandBox
from chroma_agent.chroma_common.lib import util


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
        zpool_names = set()
        try:
            zpool_names.update(self._search_for_active())
            zpool_names.update(self._search_for_inactive())

            for zpool_name in zpool_names:
                with ZfsDevice(zpool_name, True) as zfs_device:
                    if zfs_device.available:
                        out = AgentShell.try_run(["zpool", "list", "-H", "-o", "name,size,guid,health", zpool_name])
                        self._add_zfs_pool(out, block_devices)
        except OSError:                 # OSError occurs when ZFS is not installed.
            self._zpools = {}
            self._datasets = {}
            self._zvols = {}

    def _search_for_active(self):
        """ Return list of active/imported zpool names """
        out = AgentShell.try_run(["zpool", "list", "-H", "-o", "name"])

        return [line.strip() for line in filter(None, out.split('\n'))]

    def _search_for_inactive(self):
        """
        Return list of importable zpool names by parsing the 'zpool import' command output

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
        #
        #  ... (repeats for all discovered zpools)
        """
        try:
            out = AgentShell.try_run(["zpool", "import"])
        except AgentShell.CommandExecutionError as e:
            # zpool import errors with error code 1 if nothing available to import
            if e.result.rc == 1:
                out = ""
            else:
                raise e

        zpool_names = []
        zpool_name = None

        for line in filter(None, out.split("\n")):
            match = re.match("(\s*)pool: (\S*)", line)
            if match is not None:
                zpool_name = match.group(2)

            match = re.match("(\s*)state: (\S*)", line)
            if match is not None:
                if zpool_name:
                    if match.group(2) in self.acceptable_health:
                        zpool_names.append(zpool_name)
                    else:
                        daemon_log.warning("Not scanning zpool %s because it is %s." % (zpool_name, match.group(2)))
                else:
                    daemon_log.warning("Found a zpool import state but had no zpool name")

                # After each 'state' line is encountered, move onto the next zpool name
                zpool_name = None

        return zpool_names

    def _add_zfs_pool(self, line, block_devices):
        pool, size_str, uuid, health = line.split()

        if health in self.acceptable_health:
            size = util.human_to_bytes(size_str)

            drive_mms = block_devices.paths_to_major_minors(self._get_all_zpool_devices(pool))

            if drive_mms is None:
                daemon_log.warn("Could not find major minors for zpool '%s'" % pool)
                return

            # This will need discussion, but for now fabricate a major:minor. Do we ever use them as numbers?
            block_device = "zfspool:%s" % pool

            datasets = self._get_zpool_datasets(pool, uuid, drive_mms, block_devices)
            zvols = self._get_zpool_zvols(pool, drive_mms, uuid, block_devices)

            if (datasets == {}) and (zvols == {}):
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
                }

            if datasets != {}:
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

    def _get_all_zpool_devices(self, name):
        """
        Retrieve devices and children from base block devices used to create zpool

        Identify and remove partition suffix, we are only interested in the device

        :param name: zpool name
        :return: list of all devices related to the given zpool
        """
        fullpaths = self._list_zpool_devices(name, True)

        devices = []
        for basename in self._list_zpool_devices(name, False):
            fullpath = next(fullpath for fullpath in fullpaths if os.path.basename(fullpath).startswith(basename))
            device_path = os.path.join(os.path.dirname(fullpath), basename)
            devices.extend(self.find_device_and_children(device_path))
            fullpaths.remove(fullpath)

        return devices

    def _list_zpool_devices(self, name, full_paths):
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

        # ignore the first (zpool name) and last (newline character) line of command output
        return sorted([line.split()[0] for line in out.split('\n')[1:-1]], key=len, reverse=True)

    def _get_zpool_datasets(self, pool_name, zpool_uuid, drives, block_devices):
        out = AgentShell.try_run(['zfs', 'list', '-H', '-o', 'name,avail,guid'])

        zpool_datasets = {}

        if out.strip() != "no datasets available":
            for line in filter(None, out.split('\n')):
                name, size_str, uuid = line.split()
                size = util.human_to_bytes(size_str)

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
    def _get_zpool_zvols(self, pool_name, zpool_uuid, drives, block_devices):
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

    def find_device_and_children(self, device_path):
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
