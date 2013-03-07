import xmlrpclib
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api.identifiers import AutoId, GlobalId
from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api import statistics
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api import relations
import random

SIMULATOR_PORT = 8743


"""
This storage plugin interacts with the cluster simulator.

It talks to the simulator using XMLRPC to poll fake controllers, which are set up
by the simulator/benchmark code to match servers/volumes.

"""


class Couplet(resources.ScannableResource):
    class Meta:
        identifier = AutoId()

    controller_id = attributes.Integer()


class Lun(resources.LogicalDrive):
    class Meta:
        identifier = GlobalId('serial_80')
        relations = [
            relations.Provide(
                provide_to = ('linux', 'ScsiDevice'),
                attributes = ['serial_80']),
        ]
        charts = [
            {
                'title': "Bandwidth",
                'series': ['read_bytes_sec', 'write_bytes_sec']
            },
            {
                'title': "Ops",
                'series': ['read_ops_sec', 'write_ops_sec']
            },
            {
                'title': "Latency distribution",
                'series': ['write_latency_hist']
            }
        ]

    couplet = attributes.ResourceReference()
    lun_id = attributes.String()
    serial_80 = attributes.String()

    read_bytes_sec = statistics.Gauge(units="B/s", label="Read bandwidth")
    write_bytes_sec = statistics.Gauge(units="B/s", label="Write bandwidth")
    read_ops_sec = statistics.Gauge(units="op/s", label="Read operations")
    write_ops_sec = statistics.Gauge(units="op/s", label="Write operations")
    write_latency_hist = statistics.BytesHistogram(
        label="Write latency",
        bins=[(0, 16),
              (17, 32),
              (33, 64),
              (65, 128),
              (129, 256),
              (257, 512),
              (513, 1024),
              (1024, 2048),
              (2049, 4096),
              (4097, 8192),
              (8193, 16384),
              (16385, 32768)
              ])

    def get_label(self):
        return self.lun_id


class Disk(resources.PhysicalDisk):
    class Meta:
        identifier = GlobalId('wwid')

    lun = attributes.ResourceReference(optional=True)

    size = attributes.Bytes()
    wwid = attributes.Uuid()
    read_bytes_sec = statistics.Gauge(units="B/s", label="Read bandwidth")
    write_bytes_sec = statistics.Gauge(units="B/s", label="Write bandwidth")

# class ScsiLun(resources.LogicalDrive):
#     serial_80 = attributes.String()
#
#     class Meta:
#         identifier = GlobalId('serial_80')
#         relations = [relations.Provide(provide_to=('linux', 'ScsiDevice'), attributes=['serial_80'])]
#
#
# class FakePresentation(resources.PathWeight):
#     lun_id = attributes.String()
#     path = attributes.String()
#     host_id = attributes.Integer()
#
#     class Meta:
#         identifier = ScopedId('path')
#
#         relations = [
#             relations.Provide(
#                 provide_to=resources.DeviceNode,
#                 attributes=['host_id', 'path']),
#             relations.Subscribe(
#                 subscribe_to=Lun,
#                 attributes=['lun_id'])
#         ]


class SimulatorController(Plugin):
    def initial_scan(self, couplet):
        self._simulator = xmlrpclib.ServerProxy("http://localhost:%s" % SIMULATOR_PORT, allow_none = True)
        poll_data = self._simulator.poll_fake_controller(couplet.controller_id)

        self._disks = {}
        for disk_wwid, disk_data in poll_data['disks'].items():
            disk, created = self.update_or_create(Disk,
                                                  parents=[],
                                                  wwid=disk_data['wwid'],
                                                  size=disk_data['size'] * 1024 * 1024)
            self._disks[disk_wwid] = disk

        self._luns = []
        for lun_serial, lun_data in poll_data['luns'].items():
            lun, created = self.update_or_create(Lun,
                                                 parents=[couplet] + [self._disks[wwid] for wwid in lun_data['wwids']],
                                                 couplet = couplet,
                                                 serial_80=lun_data['serial'],
                                                 lun_id=lun_data['serial'],
                                                 size=lun_data['size'] * 1024 * 1024)
            for wwid in lun_data['wwids']:
                self._disks[wwid].lun = lun

            self._luns.append(lun)

    def update_scan(self, scannable_resource):
        for lun in self._luns:
            random_hist = [random.randint(0, 1000) for _ in range(0, 12)]
            lun.write_latency_hist = random_hist
            lun.read_ops_sec = random.randint(0, 1000)
            lun.write_ops_sec = random.randint(0, 1000)
            lun.read_bytes_sec = random.randint(0, 1000)
            lun.write_bytes_sec = random.randint(0, 1000)

        for disk in self._disks.values():
            disk.read_bytes_sec = random.randint(0, 1000)
            disk.write_bytes_sec = random.randint(0, 1000)
