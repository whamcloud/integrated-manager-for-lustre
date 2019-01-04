from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api import relations

version = 1


class Controller(resources.ScannableResource):
    class Meta:
        identifier = GlobalId("address")

    address = attributes.String()


class Lun(resources.LogicalDrive):
    class Meta:
        identifier = ScopedId("lun_id")

    lun_id = attributes.String()


class Presentation(resources.Resource):
    lun_id = attributes.String()
    path = attributes.String()
    host_id = attributes.Integer()

    class Meta:
        identifier = ScopedId("lun_id", "host_id")
        relations = [
            relations.Provide(provide_to=resources.DeviceNode, attributes=["host_id", "path"]),
            relations.Subscribe(subscribe_to=Lun, attributes=["lun_id"]),
        ]


class TestPlugin(Plugin):
    pass
