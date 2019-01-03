from chroma_core.lib.storage_plugin.api import attributes, statistics
from chroma_core.lib.storage_plugin.api.identifiers import GlobalId
from chroma_core.lib.storage_plugin.base_resource import BaseStorageResource, BaseScannableResource
from chroma_core.lib.storage_plugin.base_plugin import BaseStoragePlugin

version = 1


class TestScannableResource(BaseStorageResource, BaseScannableResource):
    class Meta:
        identifier = GlobalId("name")

    name = attributes.String()


class TestResource(BaseStorageResource):
    class Meta:
        identifier = GlobalId("name")

    name = attributes.String()
    thing_count = statistics.Counter()


class TestPlugin(BaseStoragePlugin):
    pass
