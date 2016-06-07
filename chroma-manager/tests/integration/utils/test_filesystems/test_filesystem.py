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

            if (cls != subtype):
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
        if 'secondary_server' in targets:
            if targets.get('failover_mode', 'failnode') == 'failnode':
                return '--failnode %s ' % targets['secondary_server']
            else:
                return '--servicenode %s --servicenode %s' % (targets['primary_server'], targets['secondary_server'])
        else:
            return ''

    @abc.abstractmethod
    def mkfs_command(self, targets, type, fsname, mgs_nids, additional_options):
        pass

    @abc.abstractproperty
    def mount_path(self):
        pass

    @property
    def install_packages_commands(cls):
        return []
