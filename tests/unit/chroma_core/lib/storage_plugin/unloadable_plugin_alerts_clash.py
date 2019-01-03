from chroma_core.lib.storage_plugin.api import attributes, alert_conditions
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId, ScopedId
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api import resources

version = 1


class Controller(resources.ScannableResource):
    class Meta:
        identifier = GlobalId("address")
        alert_conditions = [
            alert_conditions.ValueCondition("status", warn_states=["FAILED"], message="Controller failure"),
            alert_conditions.UpperBoundCondition("temperature", warn_bound=85, message="High temperature warning"),
            alert_conditions.LowerBoundCondition("temperature", warn_bound=0, message="Low temperature warning"),
            alert_conditions.ValueCondition("multi_status", warn_states=["FAIL1"], message="Failure 1"),
            alert_conditions.ValueCondition("multi_status", warn_states=["FAIL2"], message="Failure 2"),
            alert_conditions.ValueCondition("status", warn_states=["FAIL1", "FAIL2"], message="Failure 1 or 2"),
        ]

    address = attributes.String()
    status = attributes.Enum("OK", "FAILED")
    multi_status = attributes.Enum("OK", "FAIL1", "FAIL2")
    temperature = attributes.Integer(min_val=-274)


class Lun(resources.LogicalDrive):
    class Meta:
        identifier = ScopedId("lun_id")

    lun_id = attributes.String()


class Presentation(resources.Resource):
    class Meta:
        identifier = ScopedId("lun_id", "host_id")

    lun_id = attributes.String()
    path = attributes.String()
    host_id = attributes.Integer()


class TestPlugin(Plugin):
    pass
