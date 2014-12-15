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


from collections import namedtuple, defaultdict

_cached_device_types = {}


class BlockDevice(object):
    """ BlockDevice abstraction which provides blockdevice specific functionality
        This class really really really needs to be in a common place to all code
        so that its functionality can be used in all components. Then we could pass
        it around as a class and not as a hash of its values. """

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
            if (device_type == None):
                if device in _cached_device_types:
                    device_type = _cached_device_types[device]
                else:
                    device_type = 'linux'
            else:
                _cached_device_types[device] = device_type

            subtype = next(klass for klass in BlockDevice.all_subclasses() if device_type in klass._supported_device_types)

            if (cls != subtype):
                return subtype.__new__(subtype, device_type, device)
            else:
                return super(BlockDevice, cls).__new__(cls)

        except StopIteration:
            raise cls.UnknownBlockDevice("DeviceType %s unknown" % device_type)

    def __init__(self, device_type, device_path):
        self._device_type = device_type
        self._device_path = device_path

    @classmethod
    def all_subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in s.all_subclasses()]

    @property
    def filesystem_type(self):
        raise NotImplementedError("Unimplemented property - type in class %s" % type(self))

    @property
    def uuid(self):
        raise NotImplementedError("Unimplemented property - uuid in class %s" % type(self))

    @property
    def preferred_fstype(self):
        raise NotImplementedError("Unimplemented property - preferred_fstype in class %s" % type(self))

    @property
    def device_type(self):
        return self._device_type

    @property
    def device_path(self):
        return self._device_path

    def mgs_targets(self, log):
        '''
        Creates a list of all the mgs targets on a given device, returning a dict of filesystems and names
        :param log: The log to write debug info to
        :return: dict of filesystems and names
        '''
        raise NotImplementedError("Unimplemented method - mgs_targets in class %s" % type(self))

    TargetsInfo = namedtuple('TargetsInfo', ['names', 'params'])

    def targets(self, uuid_name_to_target, device, log):
        raise NotImplementedError("Unimplemented method - targets in class %s" % type(self))
