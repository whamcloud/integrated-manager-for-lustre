from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource, ScannableResource
from chroma_core.lib.storage_plugin.base_plugin import BaseStoragePlugin


class TestScannableResource(BaseStorageResource, ScannableResource):
    name = attributes.String()
    identifier = GlobalId('name')


class TestResource(BaseStorageResource):
    name = attributes.String()
    thing_count = statistics.Counter()
    identifier = GlobalId('name')


class TestPlugin(BaseStoragePlugin):
    pass
