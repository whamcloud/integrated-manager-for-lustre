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


from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api.resources import ScannableResource
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api.resources import    Controller, StoragePool, PhysicalDisk, LogicalDrive


class Resource1(ScannableResource):
    class Meta:
        identifier = GlobalId('address1', 'address2')

    address_1 = attributes.Hostname()
    address_2 = attributes.Hostname()


class Resource2(Controller):
    class Meta:
        identifier = ScopedId('index')

    index = attributes.Enum(0, 1)


class Resource3(PhysicalDisk):
    serial_number = attributes.String()
    capacity = attributes.Bytes()
    temperature = statistics.Gauge(units = 'C')

    class Meta:
        identifier = ScopedId('serial_number')


class Resource4(StoragePool):
    local_id = attributes.Integer()
    raid_type = attributes.Enum('raid0', 'raid1', 'raid5', 'raid6')
    capacity = attributes.Bytes()

    class Meta:
        identifier = ScopedId('local_id')

    def get_label(self):
        return self.local_id


class Resource5(LogicalDrive):
    local_id = attributes.Integer()
    capacity = attributes.Bytes()
    name = attributes.String()

    class Meta:
        identifier = ScopedId('local_id')

    def get_label(self):
        return self.name


class ExamplePlugin(Plugin):
    def initial_scan(self, scannable_resource):
        pass

    def update_scan(self, scannable_resource):
        pass

    def teardown(self):
        # Free any resources
        pass
