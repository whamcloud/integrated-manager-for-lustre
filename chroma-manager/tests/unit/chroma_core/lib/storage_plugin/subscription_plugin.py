from chroma_core.lib.storage_plugin.api import attributes
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api.resources import Resource, ScannableResource
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api import relations


class Controller(ScannableResource):
    address = attributes.String()
    identifier = GlobalId('address')


class Lun(resources.LogicalDrive):
    identifier = ScopedId('lun_id')
    lun_id = attributes.String()


class Presentation(Resource):
    lun_id = attributes.String()
    path = attributes.String()
    host_id = attributes.Integer()

    identifier = ScopedId('lun_id', 'host_id')

    class Meta:
        relations = [
            relations.Provide(
                provide_to = resources.DeviceNode,
                attributes = ['host_id', 'path']),
            relations.Subscribe(
                subscribe_to = Lun,
                attributes = ['lun_id'])
        ]


class TestPlugin(Plugin):
    pass
