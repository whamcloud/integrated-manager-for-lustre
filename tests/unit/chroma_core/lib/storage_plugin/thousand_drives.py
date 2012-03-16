
from chroma_core.lib.storage_plugin.plugin import StoragePlugin
from chroma_core.lib.storage_plugin.resource import StorageResource
from chroma_core.lib.storage_plugin import attributes
from chroma_core.lib.storage_plugin import statistics
from chroma_core.lib.storage_plugin.resource import GlobalId, ScannableResource, ScannableId

import random

DRIVE_COUNT = 1000


class Controller(StorageResource, ScannableResource):
    name = attributes.String()
    identifier = GlobalId('name')


class DiskDrive(StorageResource):
    identifier = ScannableId('serial')
    serial = attributes.String()
    read_bytes_sec = statistics.Gauge(units = "B/s", label = "Read bandwidth")
    write_bytes_sec = statistics.Counter(units = "B/s", label = "Write bandwidth")


class TestPlugin(StoragePlugin):
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
