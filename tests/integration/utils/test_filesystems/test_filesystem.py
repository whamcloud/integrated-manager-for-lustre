# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

import abc


class TestFileSystem(object):
    """
    Filesystem abstraction which provides filesystem specific testcode functionality

    This abstract base class is subclassed to provide concrete implementations
    of the abstract methods containing the filesystem specific behaviour.
    """

    class_override = None
    __metaclass__ = abc.ABCMeta

    _supported_filesystems = []

    class UnknownFileSystem(KeyError):
        pass

    def __new__(cls, fstype, device_path):
        try:
            subtype = next(klass for klass in TestFileSystem.__subclasses__() if fstype in klass._supported_filesystems)

            if cls != subtype:
                return subtype.__new__(subtype, fstype, device_path)
            else:
                return super(TestFileSystem, cls).__new__(cls)

        except StopIteration:
            raise cls.UnknownFileSystem("Filesystem %s unknown" % fstype)

    def __init__(self, fstype, device_path):
        self._device_path = device_path

    def _mgsnode_parameter(self, mgs_nids):
        if mgs_nids:
            return "--mgsnode=%s@tcp0" % "@tcp0:".join(mgs_nids)
        else:
            return ""

    def _failover_parameter(self, targets):
        if "secondary_server" in targets:
            if targets.get("failover_mode", "failnode") == "failnode":
                return "--failnode %s " % targets["secondary_lnet_address"]
            else:
                return "--servicenode %s --servicenode %s" % (
                    targets["lnet_address"],
                    targets["secondary_lnet_address"],
                )
        else:
            return ""

    @abc.abstractmethod
    def mkfs_command(self, targets, type, fsname, mgs_nids, additional_options):
        pass

    @abc.abstractproperty
    def mount_path(self):
        pass
