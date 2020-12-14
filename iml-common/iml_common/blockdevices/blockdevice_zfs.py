# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import logging
import os
import re
from collections import defaultdict

from blockdevice import BlockDevice
from ..lib.shell import Shell

try:
    # FIXME: this should be avoided, implicit knowledge of something outside the package
    from chroma_agent.log import daemon_log as log
except ImportError:
    log = logging.getLogger(__name__)

    if not log.handlers:
        handler = logging.FileHandler("blockdevice_zfs.log")
        handler.setFormatter(logging.Formatter("[%(asctime)s: %(levelname)s/%(name)s] %(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)


class NotZpoolException(Exception):
    pass


class BlockDeviceZfs(BlockDevice):
    # From lustre_disk.h
    LDD_F_SV_TYPE_MDT = 0x0001
    LDD_F_SV_TYPE_OST = 0x0002
    LDD_F_SV_TYPE_MGS = 0x0004
    LDD_F_SV_TYPE_MGS_or_MDT = LDD_F_SV_TYPE_MGS | LDD_F_SV_TYPE_MDT

    _supported_device_types = ["zfs"]

    def __init__(self, device_type, device_path):
        super(BlockDeviceZfs, self).__init__(device_type, device_path)

        self._zfs_properties = None
        self._zpool_properties = None

    def _check_module(self):
        Shell.try_run(["/usr/sbin/udevadm", "info", "--path=/module/zfs"])

    def _assert_zpool(self, caller_name):
        if "/" in self._device_path:
            raise NotZpoolException(
                "%s accepts zpools as device_path, '%s' is not a zpool!" % (caller_name, self._device_path)
            )

    @property
    def filesystem_info(self):
        """
        Verify if any zfs datasets exist on zpool named (self._device_path)

        :return: message describing zfs type and datasets found, None otherwise
        """
        self._check_module()

        self._assert_zpool("filesystem_info")

        try:
            device_names = Shell.try_run(["zfs", "list", "-H", "-o", "name", "-r", self._device_path]).split("\n")

            datasets = [line.split("/", 1)[1] for line in device_names if "/" in line]

            if datasets:
                return "Dataset%s '%s' found on zpool '%s'" % (
                    "s" if (len(datasets) > 1) else "",
                    ",".join(datasets),
                    self._device_path,
                )
            return None
        except OSError:  # zfs not found
            return "Unable to execute commands, check zfs is operational."
        except Shell.CommandExecutionError as e:  # no zpool 'self._device_path' found
            return str(e)

    @property
    def filesystem_type(self):
        """
        Verify if any zfs datasets exist on zpool identified by self._device_path

        :return: 'zfs' if occupied or error encountered, None otherwise
        """
        self._assert_zpool("filesystem_type")

        return self.preferred_fstype if self.filesystem_info is not None else None

    @property
    def uuid(self):
        """
        Try to retrieve the guid property of a zfs device, we will use this as the uuid for block device or file system
        objects.

        :return: uuid of zfs device (usually zpool or dataset)
        """
        self._check_module()

        out = ""

        try:
            out = Shell.try_run(["zfs", "get", "-H", "-o", "value", "guid", self._device_path])
        except OSError:  # Zfs not found.
            pass

        lines = [l for l in out.split("\n") if len(l) > 0]

        if len(lines) == 1:
            return lines[0]

        raise RuntimeError("Unable to find UUID for device %s" % self._device_path)

    @property
    def preferred_fstype(self):
        return "zfs"

    @property
    def failmode(self):
        self._check_module()

        try:
            self._assert_zpool("failmode")
        except NotZpoolException:
            blockdevice = BlockDevice(self._supported_device_types[0], self._device_path.split("/")[0])

            return blockdevice.failmode
        else:
            return Shell.try_run(["zpool", "get", "-Hp", "failmode", self._device_path]).split()[2]

    @failmode.setter
    def failmode(self, value):
        self._check_module()

        try:
            self._assert_zpool("failmode")
        except NotZpoolException:
            blockdevice = BlockDevice(self._supported_device_types[0], self._device_path.split("/")[0])

            blockdevice.failmode = value
        else:
            Shell.try_run(["zpool", "set", "failmode=%s" % value, self._device_path])

    def zfs_properties(self, reread, log=None):
        """
        Try to retrieve the properties for a zfs device at self._device_path.

        :param reread: Do not use the stored properties, always fetch them from the device
        :param log: optional logger
        :return: dictionary of zfs properties
        """
        self._check_module()

        if reread or not self._zfs_properties:
            self._zfs_properties = {}

            result = Shell.run(["zfs", "get", "-Hp", "-o", "property,value", "all", self._device_path])

            if result.rc == 0:
                for line in result.stdout.split("\n"):
                    try:
                        key, value = line.split()
                        self._zfs_properties[key] = value
                    except ValueError:  # Be resilient to things we don't understand.
                        if log:
                            log.info("zfs get for %s returned %s which was not parsable." % (self._device_path, line))

        return self._zfs_properties

    def zpool_properties(self, reread, log=None):
        """
        Try to retrieve the properties for a zpool device at self._device_path.

        :param reread: Do not use the stored properties, always fetch them from the device
        :param log: optional logger
        :return: dictionary of zpool properties
        """
        self._check_module()

        self._assert_zpool("zpool_properties")

        if reread or not self._zpool_properties:
            self._zpool_properties = {}

            ls = Shell.try_run(["zpool", "get", "-Hp", "all", self._device_path])

            for line in ls.strip().split("\n"):
                try:
                    _, key, value, _ = line.split()
                    self._zpool_properties[key] = value
                except ValueError:  # Be resilient to things we don't understand.
                    if log:
                        log.info("zpool get for %s returned %s which was not parsable." % (self._device_path, line))
                    pass

        return self._zpool_properties

    def mgs_targets(self, log):
        return {}

    def targets(self, uuid_name_to_target, device, log):
        try:
            self._check_module()
        except Shell.CommandExecutionError:
            log.info("zfs is not installed, skipping device %s" % device["path"])
            return self.TargetsInfo([], None)

        if log:
            log.info(
                "Searching device %s of type %s, uuid %s for a Lustre filesystem"
                % (device["path"], device["type"], device["uuid"])
            )

        zfs_properties = self.zfs_properties(False, log)

        if ("lustre:svname" not in zfs_properties) or ("lustre:flags" not in zfs_properties):
            if log:
                log.info("Device %s did not have a Lustre property values required" % device["path"])
            return self.TargetsInfo([], None)

        # For a Lustre block device, extract name and params
        # ==================================================
        name = zfs_properties["lustre:svname"]
        flags = int(zfs_properties["lustre:flags"])

        params = defaultdict(list)

        for zfs_property in zfs_properties:
            if zfs_property.startswith("lustre:"):
                lustre_property = zfs_property.split(":")[1]
                params[lustre_property].extend(
                    re.split(BlockDeviceZfs.lustre_property_delimiters[lustre_property], zfs_properties[zfs_property])
                )

        if name.find("ffff") != -1:
            if log:
                log.info("Device %s reported an unregistered lustre target" % device["path"])
            return self.TargetsInfo([], None)

        if (flags & self.LDD_F_SV_TYPE_MGS_or_MDT) == self.LDD_F_SV_TYPE_MGS_or_MDT:
            # For combined MGS/MDT volumes, synthesise an 'MGS'
            names = ["MGS", name]
        else:
            names = [name]

        return self.TargetsInfo(names, params)

    def import_(self, pacemaker_ha_operation):
        """
        Before importing check the device_path does not reference a dataset, if it does then retry on parent zpool
        block device.

        We can only import the zpool if it's not already imported so check before importing.

        :param pacemaker_ha_operation: This import is at the request of pacemaker. In HA operations the device may
               often have not have been cleanly exported because the previous mounted node failed in operation.
        :return: None for success meaning the zpool is imported
        """
        self._check_module()

        try:
            self._assert_zpool("import_")
        except NotZpoolException:
            blockdevice = BlockDevice(self._supported_device_types[0], self._device_path.split("/")[0])

            return blockdevice.import_(pacemaker_ha_operation)

        result = Shell.run_canned_error_message(
            ["zpool", "import"] + (["-f"] if pacemaker_ha_operation else []) + [self._device_path]
        )

        if result is not None and "a pool with that name already exists" in result:

            if self.zpool_properties(True).get("readonly") == "on":
                # Zpool is already imported readonly. Export and re-import writeable.
                result = self.export()

                if result is not None:
                    return "zpool was imported readonly, and failed to export: '%s'" % result

                result = self.import_(pacemaker_ha_operation)

                if (result is None) and (self.zpool_properties(True).get("readonly") == "on"):
                    return "zfs pool %s can only be imported readonly, is it in use?" % self._device_path

            else:
                # zpool is already imported and writable, nothing to do.
                return None

        return result

    def export(self):
        """
        Before importing check the device_path does not reference a dataset, if it does then retry on parent zpool
        block device.

        We can only export the zpool if it's already imported so check before exporting.

        :return: None for success meaning the zpool has been exported
        """
        self._check_module()

        try:
            self._assert_zpool("export")
        except NotZpoolException:
            blockdevice = BlockDevice(self._supported_device_types[0], self._device_path.split("/")[0])

            return blockdevice.export()

        result = Shell.run_canned_error_message(["zpool", "export", self._device_path])

        if result is not None and "no such pool" in result:
            # Already not imported, nothing to do
            return None

        return result

    @classmethod
    def initialise_driver(cls, managed_mode):
        """
        SPL Multi-Mount Protection for ZFS requires a hostid

        :return: None on success, error message on failure
        """
        if managed_mode and os.path.isfile("/etc/hostid") is False:
            # only create an ID if one doesn't already exist
            result = Shell.run(["genhostid"])

            if result.rc != 0:
                return "Error preparing nodes for ZFS multimount protection. gethostid failed with %s" % result.stderr

    @classmethod
    def terminate_driver(cls):
        return None
