
from configure.lib.storage_plugin.plugin import StoragePlugin
from configure.lib.storage_plugin.resource import StorageResource
from configure.lib.storage_plugin import attributes
from configure.lib.storage_plugin import statistics
from configure.lib.storage_plugin.resource import GlobalId, ScannableResource


class TestScannableResource(StorageResource, ScannableResource):
    name = attributes.String()
    identifier = GlobalId('name')


class TestResource(StorageResource):
    name = attributes.String()
    thing_count = statistics.Counter()
    identifier = GlobalId('name')


class TestPlugin(StoragePlugin):
    pass
