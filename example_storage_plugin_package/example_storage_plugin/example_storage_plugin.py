# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api.resources import ScannableResource
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api.resources import Controller, StoragePool, PhysicalDisk, LogicalDrive


class Resource1(ScannableResource):
    class Meta:
        identifier = GlobalId("address1", "address2")

    address_1 = attributes.Hostname()
    address_2 = attributes.Hostname()


class Resource2(Controller):
    class Meta:
        identifier = ScopedId("index")

    index = attributes.Enum(0, 1)


class Resource3(PhysicalDisk):
    serial_number = attributes.String()
    capacity = attributes.Bytes()
    temperature = statistics.Gauge(units="C")

    class Meta:
        identifier = ScopedId("serial_number")


class Resource4(StoragePool):
    local_id = attributes.Integer()
    raid_type = attributes.Enum("raid0", "raid1", "raid5", "raid6")
    capacity = attributes.Bytes()

    class Meta:
        identifier = ScopedId("local_id")

    def get_label(self):
        return self.local_id


class Resource5(LogicalDrive):
    local_id = attributes.Integer()
    capacity = attributes.Bytes()
    name = attributes.String()

    class Meta:
        identifier = ScopedId("local_id")

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
