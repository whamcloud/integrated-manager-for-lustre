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
import threading
import glob

from collections import defaultdict

from ..lib import shell
from blockdevice import BlockDevice


class ExportedZfsDevice(object):
    """
    This allows the enclosed code to read the status, attributes etc of a zfs device that is not currently imported to the machine.
    The code imports in read only mode and then exports the device whilst the enclosed code can then operate on the device as if
    it was locally active.
    """
    import_lock = threading.RLock()

    def __init__(self, device_path):
        self.pool_path = device_path.split('/')[0]
        self.lock_acquired = False

    def __enter__(self):
        imported_pools = shell.Shell.try_run(["zpool", "list", "-H", "-o", "name"]).split('\n')

        if self.pool_path not in imported_pools:
            try:
                self.lock_acquired = ExportedZfsDevice.import_lock.acquire()
                shell.Shell.try_run(['zpool', 'import', '-f', '-o', 'readonly=on', self.pool_path])
            except shell.Shell.CommandExecutionError:
                if self.lock_acquired:
                    ExportedZfsDevice.import_lock.release()
                    self.lock_acquired = False
                return False

        return True

    def __exit__(self, type, value, traceback):
        if self.lock_acquired:
            shell.Shell.try_run(['zpool', 'export', self.pool_path])
            ExportedZfsDevice.import_lock.release()
            self.lock_acquired = False


class NotZpoolException(Exception):
    pass


class BlockDeviceZfs(BlockDevice):
    # From lustre_disk.h
    LDD_F_SV_TYPE_MDT = 0x0001
    LDD_F_SV_TYPE_OST = 0x0002
    LDD_F_SV_TYPE_MGS = 0x0004
    LDD_F_SV_TYPE_MGS_or_MDT = (LDD_F_SV_TYPE_MGS | LDD_F_SV_TYPE_MDT)

    _supported_device_types = ['zfs']

    def __init__(self, device_type, device_path):
        super(BlockDeviceZfs, self).__init__(device_type, device_path)

        self._modules_initialized = False
        self._zfs_properties = None

    def _initialize_modules(self):
        if not self._modules_initialized:
            shell.Shell.try_run(['modprobe', 'osd_zfs'])
            shell.Shell.try_run(['modprobe', 'zfs'])

            self._modules_initialized = True

    def _assert_zpool(self, caller_name):
        if '/' in self._device_path:
            raise NotZpoolException("%s accepts zpools as device_path, '%s' is not a zpool!" % (caller_name,
                                                                                                self._device_path))

    @property
    def filesystem_info(self):
        """
        Verify if any zfs datasets exist on zpool named (self._device_path)

        :return: message describing zfs type and datasets found, None otherwise
        """
        self._assert_zpool('filesystem_info')

        try:
            device_names = shell.Shell.try_run(['zfs', 'list', '-H', '-o', 'name', '-r', self._device_path]).split('\n')

            datasets = [line.split('/', 1)[1] for line in device_names if '/' in line]

            if datasets:
                return "Dataset%s '%s' found on zpool '%s'" % ('s' if (len(datasets) > 1) else '',
                                                               ','.join(datasets),
                                                               self._device_path)
            return None
        except OSError:                             # zfs not found
            return "Unable to execute commands, check zfs is installed."
        except shell.Shell.CommandExecutionError as e:    # no zpool 'self._device_path' found
            return str(e)

    @property
    def filesystem_type(self):
        """
        Verify if any zfs datasets exist on zpool identified by self._device_path

        :return: 'zfs' if occupied or error encountered, None otherwise
        """
        self._assert_zpool('filesystem_type')

        return self.preferred_fstype if self.filesystem_info is not None else None

    @property
    def uuid(self):
        """
        Try to retrieve the guid property of a zfs device, we will use this as the uuid for block device or file system
        objects.

        :return: uuid of zfs device (usually zpool or dataset)
        """
        out = ""
        try:
            out = shell.Shell.try_run(['zfs', 'get', '-H', '-o', 'value', 'guid', self._device_path])
        except OSError:                                     # Zfs not found.
            pass
        except shell.Shell.CommandExecutionError:                 # Error is probably because device is not imported.
            with ExportedZfsDevice(self.device_path) as available:
                if available:
                    out = shell.Shell.try_run(['zfs', 'get', '-H', '-o', 'value', 'guid', self._device_path])

        lines = [l for l in out.split("\n") if len(l) > 0]

        if len(lines) == 1:
            return lines[0]

        raise RuntimeError("Unable to find UUID for device %s" % self._device_path)

    @property
    def preferred_fstype(self):
        return 'zfs'

    def zfs_properties(self, log=None):
        """
        Try to retrieve the properties for a zfs device at self._device_path.

        :param log: optional logger
        :return: dictionary of zfs properties
        """
        if not self._zfs_properties:
            self._zfs_properties = {}

            try:
                ls = shell.Shell.try_run(["zfs", "get", "-Hp", "-o", "property,value", "all", self._device_path])
            except OSError:                                     # Zfs not found.
                return self._zfs_properties
            except shell.Shell.CommandExecutionError:                 # Error is probably because device is not imported.
                with ExportedZfsDevice(self.device_path) as available:
                    if available:
                        ls = shell.Shell.try_run(["zfs", "get", "-Hp", "-o", "property,value", "all", self._device_path])
                    else:
                        return self._zfs_properties

            for line in ls.split("\n"):
                try:
                    key, value = line.split('\t')

                    self._zfs_properties[key] = value
                except ValueError:                              # Be resilient to things we don't understand.
                    if log:
                        log.info("zfs get for %s returned %s which was not parsable." % (self._device_path, line))
                    pass

        return self._zfs_properties

    def mgs_targets(self, log):
        return {}

    def targets(self, uuid_name_to_target, device, log):
        self._initialize_modules()

        if log:
            log.info("Searching device %s of type %s, uuid %s for a Lustre filesystem" % (device['path'],
                                                                                          device['type'],
                                                                                          device['uuid']))

        zfs_properties = self.zfs_properties(log)

        if ('lustre:svname' not in zfs_properties) or ('lustre:flags' not in zfs_properties):
            if log:
                log.info("Device %s did not have a Lustre property values required" % device['path'])
            return self.TargetsInfo([], None)

        # For a Lustre block device, extract name and params
        # ==================================================
        name = zfs_properties['lustre:svname']
        flags = int(zfs_properties['lustre:flags'])

        params = defaultdict(list)

        for zfs_property in zfs_properties:
            if zfs_property.startswith('lustre:'):
                lustre_property = zfs_property.split(':')[1]
                params[lustre_property].extend(re.split(BlockDeviceZfs.lustre_property_delimiters[lustre_property],
                                                        zfs_properties[zfs_property]))

        if name.find("ffff") != -1:
            if log:
                log.info("Device %s reported an unregistered lustre target" % device['path'])
            return self.TargetsInfo([], None)

        if (flags & self.LDD_F_SV_TYPE_MGS_or_MDT) == self.LDD_F_SV_TYPE_MGS_or_MDT:
            # For combined MGS/MDT volumes, synthesise an 'MGS'
            names = ["MGS", name]
        else:
            names = [name]

        return self.TargetsInfo(names, params)

    def import_(self):
        """
        Before importing check the device_path does not reference a dataset, if it does then retry on parent zpool
        block device.

        We can only import the zpool if it's not already imported so check before importing.

        :return: None for success meaning the zpool is imported
        """
        self._initialize_modules()

        try:
            self._assert_zpool('import_')
        except NotZpoolException:
            blockdevice = BlockDevice(self._supported_device_types[0], self._device_path.split('/')[0])

            return blockdevice.import_()

        try:
            shell.Shell.try_run(['zpool', 'list', self._device_path])
            return None                                     # zpool is already imported so nothing to do.
        except shell.Shell.CommandExecutionError:
            return shell.Shell.run_canned_error_message(['zpool', 'import', self._device_path])

    def export(self):
        """
        Before importing check the device_path does not reference a dataset, if it does then retry on parent zpool
        block device.

        We can only export the zpool if it's already imported so check before exporting.

        :return: None for success meaning the zpool has been exported
        """
        self._initialize_modules()

        try:
            self._assert_zpool('export')
        except NotZpoolException:
            blockdevice = BlockDevice(self._supported_device_types[0], self._device_path.split('/')[0])

            return blockdevice.export()

        try:
            shell.Shell.try_run(['zpool', 'list', self._device_path])
        except shell.Shell.CommandExecutionError:
            return None                                     # zpool is not imported so nothing to do.

        return shell.Shell.run_canned_error_message(['zpool', 'export', self._device_path])

    def purge_filesystem_configuration(self, filesystem_name, log):
        """
        Purge the details of the filesystem from the mgs blockdevice.  This routine presumes that the blockdevice
        is the mgs_blockdevice and does not make any checks

        :param filesystem_name: The name of the filesystem to purge
        :param log: The logger to use for log messages.
        :return: None on success or error message
        """

        try:
            shell_result = shell.Shell.run(["zfs", "canmount=on", self._device_path])

            if shell_result.rc != 0:
                return "ZFS failed to set canmount=on property on device %s, error was %s" % \
                       (self._device_path, shell_result.stderr)

            shell_result = shell.Shell.run(["zfs", "mount", self._device_path])

            if shell_result.rc != 0:
                return "ZFS failed to mount device %s, error was %s" % (self._device_path, shell_result.stderr)

            for config_entry in glob.glob("/%s/CONFIGS/%s-*" % (self._device_path, filesystem_name)):
                shell_result = shell.Shell.run(["rm", config_entry])

                if shell_result.rc != 0:
                    return "ZFS failed to purge filesystem (%s) information from device %s, error was %s" % \
                           (filesystem_name, self._device_path, shell_result.stderr)
        finally:
            # Try both these commands, report failure but we really don't have a way out if they fail.
            shell_result_unmount = shell.Shell.run(["zfs", "unmount", self._device_path])
            shell_result_canmount = shell.Shell.run(["zfs", "canmount=off", self._device_path])

            if shell_result_unmount.rc != 0:
                return "ZFS failed to unmount device %s, error was %s" % (self._device_path, shell_result_unmount.stderr)

            if shell_result_canmount.rc != 0:
                return "ZFS failed to set canmount=off property on device %s, error was %s" % \
                       (self._device_path, shell_result_canmount.stderr)

        return None
