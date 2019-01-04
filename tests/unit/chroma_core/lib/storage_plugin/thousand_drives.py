from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api.plugin import Plugin

import random


DRIVE_COUNT = 1000

version = 1


class Controller(resources.ScannableResource):
    class Meta:
        identifier = GlobalId("name")

    name = attributes.String()


class DiskDrive(resources.Resource):
    class Meta:
        identifier = ScopedId("serial")
        charts = [{"title": "Bandwidth", "series": ["read_bytes_sec", "write_bytes_sec"]}]

    serial = attributes.String()
    read_bytes_sec = statistics.Gauge(units="B/s", label="Read bandwidth")
    write_bytes_sec = statistics.Counter(units="B/s", label="Write bandwidth")


class TestPlugin(Plugin):
    def initial_scan(self, controller):
        self.drives = []
        for i in xrange(0, DRIVE_COUNT):
            serial = "%s_%d" % (controller.name, i)
            drive, created = self.update_or_create(DiskDrive, serial=serial)
            self.drives.append(drive)

    def update_scan(self, controller):
        for drive in self.drives:
            drive.read_bytes_sec = random.randint(0, 1000)
            drive.write_bytes_sec = random.randint(0, 1000)
