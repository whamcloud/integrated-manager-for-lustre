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

import errno
import glob
import os
import stat
import time

import chroma_agent.lib.normalize_device_path as ndp
from chroma_agent.log import daemon_log


class DeviceHelper(object):
    MAPPERPATH = os.path.join('/dev', 'mapper')
    DISKBYIDPATH = os.path.join('/dev', 'disk', 'by-id')
    DISKBYPATHPATH = os.path.join('/dev', 'disk', 'by-path')
    MDRAIDPATH = os.path.join('/dev', 'md')
    DEVPATH = '/dev'
    MAXRETRIES = 5
    non_existent_paths = set([])

    """Base class with common methods for the various device detecting classes used
       by this plugin"""

    def _dev_major_minor(self, path):
        """Return a string if 'path' is a block device or link to one, else return None"""

        file_state = None
        retries = self.MAXRETRIES
        while retries > 0:
            try:
                file_state = os.stat(path)

                if path in self.non_existent_paths:
                    self.non_existent_paths.discard(path)
                    daemon_log.debug('New device started to respond %s' % path)

                break
            except OSError as os_error:
                if os_error.errno not in [errno.ENOENT, errno.ENOTDIR]:
                    raise

                # An OSError could be raised because a path genuinely doesn't
                # exist, but it also can be the result of conflicting with
                # actions that cause devices to disappear momentarily, such as
                # during a partprobe while it reloads the partition table.
                # So we retry for a short window to catch those devices that
                # just disappear momentarily.
                time.sleep(0.1)
                retries -= retries if path in self.non_existent_paths else 1

        if file_state is None:
            if path not in self.non_existent_paths:
                self.non_existent_paths.add(path)
                daemon_log.debug('New device failed to respond %s' % path)

            return None
        elif stat.S_ISBLK(file_state.st_mode):
            return "%d:%d" % (os.major(file_state.st_rdev), os.minor(file_state.st_rdev))
        else:
            return None

    def _paths_to_major_minors(self, device_paths):
        """
        Create a list of device major minors for a list of device paths. If any of the paths come
        back as None, return an empty list.

        :param device_paths: The list of paths to get the list of major minors for.
        :return: list of dev_major_minors, or an empty list if any device_path is not found.
        """
        device_mms = []
        for device_path in device_paths:
            device_mm = self._dev_major_minor(device_path)

            if device_mm is None:
                return []

            device_mms.append(device_mm)
        return device_mms

    def _find_block_devs(self, folder):
        # Map of major_minor to path
        result = {}
        for path in glob.glob(os.path.join(folder, "*")):
            mm = self._dev_major_minor(path)
            if mm:
                result[mm] = path

        return result

    """ This function needs a good name. It takes a bunch of devices like MdRaid, EMCPower which
    are effectively composite devices made up from a collection of other devices and returns that
    list with the drives and everything nicely assembled. """
    def _composite_device_list(self, source_devices):
        devices = {}

        for device in source_devices:
            drive_mms = self._paths_to_major_minors(device['device_paths'])
            if drive_mms:
                devices[device['uuid']] = {'path': device["path"],
                                           'block_device': device['mm'],
                                           'drives': drive_mms}

                # Finally add these devices to the canonical path list.
                for device_path in device['device_paths']:
                    ndp.add_normalized_device(device_path, device['path'])

        return devices

    def _human_to_bytes(self, value_str):
        """ Convert something like 1024b, or 1024m to a number of bytes
            Very straight forward takes the index into the conversion strings and uses that as the 1024 power"""
        conversion = "bkmgtp"

        value = float(value_str[0:-1])
        index = conversion.index(value_str[-1:].lower())

        return int(value * (1024 ** index))
