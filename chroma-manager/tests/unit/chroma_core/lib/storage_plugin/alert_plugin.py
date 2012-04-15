from chroma_core.lib.storage_plugin.api import attributes, alert_conditions
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api.resources import Resource, ScannableResource
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api import resources


class Controller(ScannableResource):
    address = attributes.String()
    identifier = GlobalId('address')

    status = attributes.Enum('OK', 'FAILED')
    temperature = attributes.Integer(min_val = -274)

    failure = alert_conditions.ValueCondition('status',
        warn_states = ['FAILED'], message = "Controller failure")

    boiling = alert_conditions.UpperBoundCondition('temperature',
        warn_bound = 85, message = "High temperature warning")

    freezing = alert_conditions.LowerBoundCondition('temperature',
        warn_bound = 0, message = "Low temperature warning")


class Lun(resources.LogicalDrive):
    identifier = ScopedId('lun_id')
    lun_id = attributes.String()


class Presentation(Resource):
    lun_id = attributes.String()
    path = attributes.String()
    host_id = attributes.Integer()

    identifier = ScopedId('lun_id', 'host_id')


class TestPlugin(Plugin):
    pass
