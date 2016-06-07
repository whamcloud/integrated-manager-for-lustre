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

import abc


class TestBlockDevice(object):
    """
    BlockDevice abstraction which provides blockdevice specific test code
    functionality

    This abstract base class is subclassed to provide concrete implementations
    of the abstract methods containing the blockdevice specific behaviour.
    """

    class_override = None
    __metaclass__ = abc.ABCMeta

    _supported_device_types = []

    class UnknownBlockDevice(KeyError):
        pass

    def __new__(cls, device_type, device):
        try:
            subtype = next(klass for klass in TestBlockDevice.__subclasses__() if device_type in klass._supported_device_types)

            if (cls != subtype):
                return subtype.__new__(subtype, device_type, device)
            else:
                return super(TestBlockDevice, cls).__new__(cls)

        except StopIteration:
            raise cls.UnknownBlockDevice("DeviceType %s unknown" % device_type)

    def __init__(self, device_type, device_path):
        self._device_type = device_type
        self._device_path = device_path

    @abc.abstractproperty
    def preferred_fstype(self):
        pass

    @property
    def device_path(self):
        return self._device_path

    @classmethod
    def clear_device_commands(cls, device_paths):
        return []

    @property
    def prepare_device_commands(self):
        return []

    @classmethod
    def all_clear_device_commands(cls, device_paths):
        commands = []

        for klass in TestBlockDevice.__subclasses__():
            commands = commands + klass.clear_device_commands(device_paths)

        return commands

    @property
    def install_packages_commands(self):
        return []

    @property
    def release_commands(self):
        return []

    @property
    def capture_commands(self):
        return []
