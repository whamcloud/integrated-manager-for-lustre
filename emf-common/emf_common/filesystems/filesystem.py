# Copyright (c) 2020 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from ..lib.shell import Shell
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

    RC_MOUNT_SUCCESS = 0
    RC_MOUNT_INPUT_OUTPUT_ERROR = 5
    RC_MOUNT_ENOENT_ERROR = 2
    RC_MOUNT_ESHUTDOWN_ERROR = 108

    class_override = None
    __metaclass__ = abc.ABCMeta

    class UnknownFileSystem(KeyError):
        pass

    def __new__(cls, fstype, device_path):
        try:
            # It is possible the caller doesn't know the device type, but they do know the path - these cases should be
            # avoided but in EMF today this is the case, so keep a class variable to allow use to resolve it. We default
            # very badly to ldiskfs if we don't have a value.
            if fstype is None:
                if device_path in _cached_filesystem_types:
                    fstype = _cached_filesystem_types[device_path]
                else:
                    fstype = "ldiskfs"
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
        """ Returns the label of the filesystem """
        pass

    def device_path(self):
        """ The path to the device the contains/will contain the filesystem """
        return self._device_path

    @property
    def inode_size(self):
        """ The inode size of the filesystem, returns 0 if inode size not supported """
        return 0

    @property
    def inode_count(self):
        """ The inode count of the filesystem, returns 0 if inode count not supported """
        return 0

    def mount(self, mount_point):
        """ Mount the file system, raise an exception on error. """
        result = Shell.run(["mount", "-t", "lustre", self._device_path, mount_point])

        if result.rc in [self.RC_MOUNT_INPUT_OUTPUT_ERROR, self.RC_MOUNT_ENOENT_ERROR, self.RC_MOUNT_ESHUTDOWN_ERROR]:
            # HYD-1040, LU-9838, LU-9976: Sometimes we should retry on a failed registration
            result = Shell.run(["mount", "-t", "lustre", self._device_path, mount_point])

        if result.rc != self.RC_MOUNT_SUCCESS:
            raise RuntimeError(
                "Error (%s) mounting '%s': '%s' '%s'" % (result.rc, mount_point, result.stdout, result.stderr)
            )

    def umount(self):
        """ :return: Umount the file system, raise an exception on error. """
        return Shell.try_run(["umount", self._device_path])

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
