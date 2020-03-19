from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api.identifiers import ScopedId, AutoId, GlobalId
from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api import relations

version = 1


def crypt(password):
    return password.upper()


class Couplet(resources.ScannableResource):
    class Meta:
        identifier = AutoId()

    address = attributes.Hostname()
    password = attributes.Password(crypt)
    internal_id = attributes.String(user_read_only=True, optional=True)


class Lun(resources.LogicalDrive):
    class Meta:
        identifier = ScopedId("lun_id")

    lun_id = attributes.String()
    couplet = attributes.ResourceReference()

    def get_label(self):
        return self.lun_id


class ScsiLun(resources.LogicalDrive):
    serial = attributes.String()

    class Meta:
        identifier = GlobalId("serial")
        relations = [relations.Provide(provide_to=("linux", "ScsiDevice"), attributes=["serial"])]


class FakePresentation(resources.PathWeight):
    lun_id = attributes.String()
    path = attributes.String()
    host_id = attributes.Integer()
    # FIXME: allow subscribers to use different name for their attributes than the provider did

    class Meta:
        identifier = ScopedId("path")

        relations = [
            relations.Provide(provide_to=resources.DeviceNode, attributes=["host_id", "path"]),
            relations.Subscribe(subscribe_to=Lun, attributes=["lun_id"]),
        ]


class FakeVirtualMachine(resources.VirtualMachine):
    class Meta:
        identifier = ScopedId("address")


class FakeControllerPlugin(Plugin):
    def initial_scan(self, couplet):
        # hosts = ['flint01', 'flint02']
        # for host in hosts:
        #    self.update_or_create(FakeVirtualMachine, address = host)

        luns = ["lun_rhubarb1", "lun_rhubarb2"]
        self._luns = []
        for lun in luns:
            lun, creaated = self.update_or_create(
                Lun, parents=[couplet], lun_id=lun, size=73 * 1024 * 1024 * 1024, couplet=couplet
            )
            self._luns.append(lun)

        self.update_or_create(ScsiLun, serial="SQEMU    QEMU HARDDISK  MPATH-testdev01", size=73 * 1024 * 1024 * 1024)

    def update_scan(self, scannable_resource):
        import random

        for lun in self._luns:
            random_hist = [random.randint(0, 1000) for i in range(0, 12)]
            lun.write_latency_hist = random_hist
            lun.read_bytes_sec = random.randint(0, 1000)
            lun.write_bytes_sec = random.randint(0, 1000)

    def teardown(self):
        pass

    def agent_session_start(self, host_id, data):
        for device_node in data:
            self.update_or_create(
                FakePresentation,
                path=device_node["node_path"],
                host_id=host_id,
                lun_id=device_node["lun_id"],
                weight=device_node["weight"],
            )

    def agent_session_continue(self, host_resource, data):
        pass
