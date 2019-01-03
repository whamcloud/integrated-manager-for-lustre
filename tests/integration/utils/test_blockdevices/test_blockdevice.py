# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

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
            subtype = next(
                klass for klass in TestBlockDevice.__subclasses__() if device_type in klass._supported_device_types
            )

            if cls != subtype:
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
    def wipe_device_commands(self):
        return ["wipefs -a {}".format(self._device_path), "udevadm settle"]

    @property
    def create_device_commands(self):
        return []

    @property
    def reset_device_commands(self):
        return self.wipe_device_commands + self.create_device_commands

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
    def remove_packages_commands(self):
        return []

    @property
    def release_commands(self):
        return []

    @property
    def capture_commands(self):
        return []

    @property
    def destroy_commands(self):
        return []
