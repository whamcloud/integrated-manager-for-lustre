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

import glob
import os

import chroma_agent.lib.normalize_device_path as ndp


class DeviceHelper(object):
    MAPPERPATH = os.path.join('/dev', 'mapper')
    DISKBYIDPATH = os.path.join('/dev', 'disk', 'by-id')
    DISKBYPATHPATH = os.path.join('/dev', 'disk', 'by-path')
    MDRAIDPATH = os.path.join('/dev', 'md')
    DEVPATH = '/dev'

    """Base class with common methods for the various device detecting classes used
       by this plugin"""

    def _dev_major_minor(self, path):
        """Return a string if 'path' is a block device or link to one, else return None"""
        from stat import S_ISBLK
        try:
            s = os.stat(path)
        except OSError:
            return None

        if S_ISBLK(s.st_mode):
            return "%d:%d" % (os.major(s.st_rdev), os.minor(s.st_rdev))
        else:
            return None

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
            drives = [self._dev_major_minor(dp) for dp in device['device_paths']]

            # Check that none of the drives in the list are None (i.e. not found) if we found them all
            # then we create the entry.
            if drives.count(None) == 0:
                devices[device['uuid']] = {'path': ndp.normalized_device_path(device["path"]),
                                           'block_device': device['mm'],
                                           'drives': drives}

                # Finally add these devices to the canonical path list.
                for device_path in device['device_paths']:
                    ndp.add_normalized_device(device_path, device['path'])

        return devices
