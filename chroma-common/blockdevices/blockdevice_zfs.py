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

from ..lib import shell
from blockdevice import BlockDevice


class BlockDeviceZfs(BlockDevice):
    _supported_device_types = ['zfs']

    def __init__(self, device_type, device_path):
        self._zdb_values = None

        super(BlockDeviceZfs, self).__init__(device_type, device_path)

    @property
    def filesystem_type(self):
        # We should verify the value, but for now lets just presume.
        return 'zfs'

    @property
    def uuid(self):
        out = shell.try_run(['zfs', 'list', '-o', 'name,guid'])
        lines = [l for l in out.split("\n") if len(l) > 0]
        for line in lines:
            result = re.search("^%s\s+(.+)" % self._device_path, line)
            if (result):
                return result.group(1)

        raise RuntimeError("Unabled to find UUID for device %s" % self._device_path)

    @property
    def preferred_fstype(self):
        return 'zfs'

    @property
    def zdb_values(self):
        if not self._zdb_values:
            self._zdb_values = {}

            # First get the id for the dataset
            try:
                ls = shell.try_run(["zdb", "-h", self._device_path])
            except (shell.CommandExecutionError, OSError):          # Errors or zdb not found.
                try:
                    ls = shell.try_run(["zdb", "-e", "-h", self._device_path])
                except (shell.CommandExecutionError, OSError):      # Errors or zdb not found.
                    return self._zdb_values

            dataset_id = None

            for line in ls.split("\n"):
                match = re.search("ID ([\w-]+)", line)

                if match:
                    dataset_id = match.group(1)
                    break

            if dataset_id:
                try:
                    ls = shell.try_run(["zdb", "-h", self._device_path.split("/")[0]])
                except shell.CommandExecutionError:
                    ls = shell.try_run(["zdb", "-e", "-h", self._device_path.split("/")[0]])

                for line in ls.split("\n"):
                    try:
                        match = re.search("lustre:([\w-]+)=([^\s]+) dataset = ([\w-]+)", line)

                        if (match is not None) and (match.group(3) == dataset_id):
                            self._zdb_values[match.group(1)] = match.group(2)

                    except IndexError:
                        pass

        return self._zdb_values

    def mgs_targets(self, log):
        zdb_values = self.zdb_values

        if ('fsname' in zdb_values) and ('svname' in zdb_values):
            return {zdb_values['fsname']: {"name": zdb_values['svname'][len(zdb_values['fsname']) + 1:]}}
        else:
            return {}

    def targets(self, uuid_name_to_target, device, log):
        log.info("Searching device %s of type %s, uuid %s for a Lustre filesystem" % (device['path'], device['type'], device['uuid']))

        zdb_values = self.zdb_values

        if ('svname' not in zdb_values) or ('flags' not in zdb_values):
            log.info("Device %s did not have a Lustre zdb values required" % device['path'])
            return self.TargetsInfo([], None)

        # For a Lustre block device, extract name and params
        # ==================================================
        name = zdb_values['svname']
        flags = int(zdb_values['flags'], 16)

        if  ('mgsnode' in zdb_values):
            params = {'mgsnode': [zdb_values['mgsnode']]}
        else:
            params = {}

        if name.find("ffff") != -1:
            log.info("Device %s reported an unregistered lustre target and so will not be reported" % device['path'])
            return self.TargetsInfo([], None)

        if flags & 0x0005 == 0x0005:
            # For combined MGS/MDT volumes, synthesise an 'MGS'
            names = ["MGS", name]
        else:
            names = [name]

        return self.TargetsInfo(names, params)
