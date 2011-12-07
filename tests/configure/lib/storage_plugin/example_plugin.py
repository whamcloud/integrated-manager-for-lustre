
from configure.lib.storage_plugin.plugin import StoragePlugin
from configure.lib.storage_plugin.resource import StorageResource, GlobalId, ScannableResource, ScannableId
from configure.lib.storage_plugin import attributes, statistics
from configure.lib.storage_plugin import builtin_resources


class Couplet(StorageResource, ScannableResource):
    identifier = GlobalId('address1', 'address2')

    address_1 = attributes.Hostname()
    address_2 = attributes.Hostname()


class Controller(builtin_resources.Controller):
    identifier = ScannableId('index')

    index = attributes.Enum(0, 1)


class HardDrive(builtin_resources.PhysicalDisk):
    serial_number = attributes.String()
    capacity = attributes.Bytes()
    temperature = statistics.Gauge(units = 'C')

    identifier = ScannableId('serial_number')


class RaidPool(builtin_resources.StoragePool):
    local_id = attributes.Integer()
    raid_type = attributes.Enum('raid0', 'raid1', 'raid5', 'raid6')
    capacity = attributes.Bytes()

    identifier = ScannableId('local_id')

    def human_string(self):
        return self.local_id


class Lun(builtin_resources.VirtualDisk):
    local_id = attributes.Integer()
    capacity = attributes.Bytes()
    name = attributes.String()

    scsi_id = attributes.String(provide = 'scsi_serial')

    identifier = ScannableId('local_id')

    def human_string(self):
        return self.name


class ExamplePlugin(StoragePlugin):
    def initial_scan(self, scannable_resource):
        # This is where the plugin should detect all the resources
        # belonging to scannable_resource, or throw an exception
        # if that cannot be done.
        pass

    def update_scan(self, scannable_resource):
        # Update any changed or added/removed resources
        # Update any statistics
        pass

    def teardown(self):
        # Free any resources
        pass
