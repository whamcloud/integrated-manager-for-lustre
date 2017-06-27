# Copyright (c) 2017 Intel Corporation. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from collections import namedtuple, defaultdict
from ..lib import util, shell
import abc

_cached_device_types = {}


class BlockDevice(object):
    """
    BlockDevice abstraction which provides blockdevice specific functionality
    This class really really really needs to be in a common place to all code
    so that its functionality can be used in all components. Then we could pass
    it around as a class and not as a hash of its values.
    """

    class_override = None
    __metaclass__ = abc.ABCMeta

    # The split for multiple properties in the lustre configuration storage seems to be inconsistent
    # so create a look up table for the splitters.
    lustre_property_delimiters = defaultdict(lambda: "")
    lustre_property_delimiters['failover.node'] = ':'
    lustre_property_delimiters['mgsnode'] = ':'

    class UnknownBlockDevice(KeyError):
        pass

    def __new__(cls, device_type, device):
        try:
            # It is possible the caller doesn't know the device type, but they do know the path - these cases should be
            # avoided but in IML today this is the case, so keep a class variable to allow use to resolve it. We default
            # very badly to linux if we don't have a value.
            if device_type == None:
                if device in _cached_device_types:
                    device_type = _cached_device_types[device]
                else:
                    device_type = 'linux'
            else:
                _cached_device_types[device] = device_type

            subtype = next(klass for klass in util.all_subclasses(BlockDevice) if device_type in klass._supported_device_types)

            if cls != subtype:
                return subtype.__new__(subtype, device_type, device)
            else:
                return super(BlockDevice, cls).__new__(cls)

        except StopIteration:
            raise cls.UnknownBlockDevice("DeviceType %s unknown" % device_type)

    def __init__(self, device_type, device_path):
        self._device_type = device_type
        self._device_path = device_path

    def _initialize_modules(self):
        """
        Called before operations that might result the filesystem specific modules to be loaded.

        :return: None
        """
        return None

    @abc.abstractproperty
    def filesystem_type(self):
        """
        Return type of occupying filesystem(s)
        """
        pass

    @abc.abstractproperty
    def filesystem_info(self):
        """
        Return message regarding occupying filesystem(s) that reside on this block device
        """
        pass

    @abc.abstractproperty
    def uuid(self):
        pass

    @abc.abstractproperty
    def preferred_fstype(self):
        pass

    @property
    def device_type(self):
        return self._device_type

    @property
    def device_path(self):
        return self._device_path

    @classmethod
    def initialise_driver(cls, managed_mode):
        return None

    @classmethod
    def terminate_driver(cls):
        return None

    @abc.abstractmethod
    def mgs_targets(self, log):
        """
        Creates a list of all the mgs targets on a given device, returning a dict of filesystems and names

        :param log: The log to write debug info to
        :return: dict of filesystems and names
        """
        pass

    TargetsInfo = namedtuple('TargetsInfo', ['names', 'params'])

    @abc.abstractmethod
    def targets(self, uuid_name_to_target, device, log):
        pass

    def import_(self, pacemaker_ha_operation):
        """
        If appropriate import the blockdevice, this is required for many devices where only 1 node may have the device
        imported at a time. zpools for example.

        :param pacemaker_ha_operation: This import is at the request of pacemaker. In HA operations the device may
               often have not have been cleanly exported because the previous mounted node failed in operation.
        :return: None on success or error message on failure
        """
        return None

    def export(self):
        """
        If appropriate export the blockdevice, this is required for many devices where only 1 node may have the device
        imported at a time. zpools for example.

        :return: None on success or error message on failure
        """
        return None

    def purge_filesystem_configuration(self, filesystem_name, log):
        """
        Purge the details of the filesystem from the mgs blockdevice.  This routine presumes that the blockdevice
        is the mgs_blockdevice and does not make any checks

        :param filesystem_name: The name of the filesystem to purge
        :param log: The logger to use for log messages.
        :return: None on success or error message on failure
        """
        shell_result = shell.Shell.run(['lctl', 'erase_lcfg', filesystem_name])

        if shell_result.rc != 0:
            return "Purge filesystem failed to purge %s with error '%s'" % (filesystem_name, shell_result.stderr)
