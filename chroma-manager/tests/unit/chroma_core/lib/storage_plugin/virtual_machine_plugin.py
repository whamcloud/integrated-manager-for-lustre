from chroma_core.lib.storage_plugin.api.identifiers import GlobalId
from chroma_core.lib.storage_plugin.api.plugin import Plugin
from chroma_core.lib.storage_plugin.api import resources
from chroma_core.lib.storage_plugin.api import attributes


class Controller(resources.Controller):
    address = attributes.String()
    identifier = GlobalId('address')


class VirtualMachine(resources.VirtualMachine):
    identifier = GlobalId('address')


class TestPlugin(Plugin):
    pass
