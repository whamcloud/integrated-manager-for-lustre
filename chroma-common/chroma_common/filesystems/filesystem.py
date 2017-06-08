# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from ..lib import shell
from ..lib import util
import abc

_cached_filesystem_types = {}


class FileSystem(object):
    """
    Filesystem abstraction which provides filesystem specific functionality
    This class really really really needs to be in a common place to all code
    so that its functionality can be used in all components. Then we could pass
    it around as a class and not as a hash of its values.
    """

    class_override = None
    __metaclass__ = abc.ABCMeta

    class UnknownFileSystem(KeyError):
        pass

    def __new__(cls, fstype, device_path):
        try:
            # It is possible the caller doesn't know the device type, but they do know the path - these cases should be
            # avoided but in IML today this is the case, so keep a class variable to allow use to resolve it. We default
            # very badly to ldiskfs if we don't have a value.
            if fstype is None:
                if device_path in _cached_filesystem_types:
                    fstype = _cached_filesystem_types[device_path]
                else:
                    fstype = 'ldiskfs'
            else:
                _cached_filesystem_types[device_path] = fstype

            subtype = next(klass for klass in util.all_subclasses(FileSystem) if fstype in klass._supported_filesystems)

            if cls != subtype:
                return subtype.__new__(subtype, fstype, device_path)
            else:
                return object.__new__(cls)

        except StopIteration:
            raise cls.UnknownFileSystem("Filesystem %s unknown" % fstype)

    def __init__(self, fstype, device_path):
        self._fstype = fstype
        self._device_path = device_path

    @abc.abstractmethod
    def label(self):
        """ :return: Returns the label of the filesystem """
        pass

    def device_path(self):
        """ :return: The path to the device the contains/will contain the filesystem """
        return self._device_path

    @property
    def inode_size(self):
        """ :return: The inode size of the filesystem, returns 0 if inode size not supported """
        return 0

    @property
    def inode_count(self):
        """ :return: The inode count of the filesystem, returns 0 if inode count not supported """
        return 0

    def mount(self, mount_point):
        """ :return: Mount the file system, raise an exception on error. """
        self._initialize_modules()

        return shell.Shell.try_run(["mount", "-t", "lustre", "%s" % self._device_path, mount_point])

    def umount(self):
        """ :return: Umount the file system, raise an exception on error. """
        self._initialize_modules()

        return shell.Shell.try_run(["umount", self._device_path])

    def mount_path(self, target_name):
        """
        :param target_name: The lustre target, ost1, ost2, mgt etc.
        :return: Returns the path to the device for mounting
        """
        return self._device_path

    @abc.abstractmethod
    def mkfs(self, target_name, options):
        """
        Runs mkfs for the filesystem catering for any fs specific irregularities.

        :param target_name: The lustre target, ost1, ost2, mgt etc.
        :param options: mkfs options to be used for the mount.
        :return:
        """
        pass

    @abc.abstractmethod
    def mkfs_options(self, target):
        """
        :param target: The target device that will be formatted.
        :return: A list of filesystem specific options required for the format.
        """
        pass

    @classmethod
    def all_supported_filesystems(self):
        """
        Walks the subclasses to find all the supported filesystems and returns these as a unique list.

        :return: set of supported file systems
        """
        supported_filesystems = []

        for klass in FileSystem.__subclasses__():
            supported_filesystems += klass._supported_filesystems

        return list(set(supported_filesystems))

    @abc.abstractmethod
    def devices_match(self, device1_path, device2_path, device2_uuid):
        """
        Verifies that the devices referenced in the parameters are the same

        :param device1_path: first device string representation
        :param device2_path: second device string representation
        :param device2_uuid: uuid of second device
        :return: return True if both device identifiers reference the same object
        """
        pass
