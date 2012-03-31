from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource, ScannableResource
from chroma_core.lib.storage_plugin.base_plugin import BaseStoragePlugin

import random

DRIVE_COUNT = 1000


class Controller(BaseStorageResource, ScannableResource):
    name = attributes.String()
    identifier = GlobalId('name')


class DiskDrive(BaseStorageResource):
    identifier = ScopedId('serial')
    serial = attributes.String()
    read_bytes_sec = statistics.Gauge(units = "B/s", label = "Read bandwidth")
    write_bytes_sec = statistics.Counter(units = "B/s", label = "Write bandwidth")

    charts = [
        {
            'title': "Bandwidth",
            'series': ['read_bytes_sec', 'write_bytes_sec']
        }
    ]


class TestPlugin(BaseStoragePlugin):
    def initial_scan(self, controller):
        self.drives = []
        for i in xrange(0, DRIVE_COUNT):
            serial = "%s_%d" % (controller.name, i)
            drive, created = self.update_or_create(DiskDrive, serial = serial)
            self.drives.append(drive)

    def update_scan(self, controller):
        for drive in self.drives:
            drive.read_bytes_sec = random.randint(0, 1000)
            drive.write_bytes_sec = random.randint(0, 1000)
