from chroma_core.lib.storage_plugin.api.identifiers import GlobalId
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api import attributes

version = 1


class Controller(resources.ScannableResource):
    class Meta:
        identifier = GlobalId("address")

    address = attributes.String()


class VirtualMachine(resources.VirtualMachine):
    class Meta:
        identifier = GlobalId("address")


class TestPlugin(Plugin):
    pass
