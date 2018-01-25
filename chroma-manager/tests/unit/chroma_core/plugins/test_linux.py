import json
import os
import re
from mock import patch, Mock
from django.utils import unittest
from toolz import compose

from chroma_core.plugins.block_devices import get_block_devices, get_drive_serials, get_host_devices, discover_zpools
from chroma_core.services.plugin_runner import ResourceManager
from chroma_core.models.host import Volume, VolumeNode
from chroma_core.models.storage_plugin import StorageResourceRecord
from tests.unit.chroma_core.helpers import synthetic_host
from tests.unit.chroma_core.helpers import load_default_profile
from tests.unit.chroma_core.lib.storage_plugin.helper import load_plugins
from chroma_core.services.plugin_runner import AgentPluginHandlerCollection
from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase


class LinuxPluginTestCase(IMLUnitTestCase):
    def setUp(self):
        super(LinuxPluginTestCase, self).setUp()

        self.manager = load_plugins(['linux', 'linux_network'])

        import chroma_core.lib.storage_plugin.manager
        self.old_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.manager

        self.resource_manager = ResourceManager()

        load_default_profile()

    def tearDown(self):
        import chroma_core.lib.storage_plugin.manager
        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.old_manager

    def __init__(self, *args, **kwargs):
        self._handle_counter = 0
        super(LinuxPluginTestCase, self).__init__(*args, **kwargs)

    def _make_global_resource(self, plugin_name, class_name, attrs):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(plugin_name, class_name)
        resource_record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, attrs)
        return resource_record

    def _start_session_with_data(self, host, data_file):
        # This test impersonates AgentDaemon (load and pass things into a plugin instance)
        data = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures/%s" % data_file)))

        plugin = AgentPluginHandlerCollection(self.resource_manager).handlers['linux']._create_plugin_instance(host)

        plugin.do_agent_session_start(data['linux'])

    def test_HYD_1269(self):
        """This test vector caused an exception during Volume generation.
        It has two block devices with the same serial_80, which should be
        caught where we scrub out the non-unique IDs that QEMU puts into
        serial_80."""
        host = synthetic_host('myaddress', storage_resource=True)
        self._start_session_with_data(host, "HYD_1269.json")
        self.assertEqual(Volume.objects.count(), 2)

    def test_HYD_1269_noerror(self):
        """This test vector is from a different machine at the same time which did not experience the HYD-1272 bug"""
        host = synthetic_host('myaddress', storage_resource=True)
        self._start_session_with_data(host, "HYD_1269_noerror.json")
        # Multiple partitioned devices, sda->sde, 2 partitions each
        # sda1 is boot, sda2 is a PV

        self.assertEqual(Volume.objects.count(), 8)
        self.assertEqual(VolumeNode.objects.count(), 8)

    def test_multipath(self):
        """Two hosts, each seeing two block devices via two nodes per block device,
        with multipath devices configured correctly"""
        host1 = synthetic_host('myaddress', storage_resource=True)
        host2 = synthetic_host('myaddress2', storage_resource=True)
        self._start_session_with_data(host1, "multipath.json")
        self._start_session_with_data(host2, "multipath.json")

        self.assertEqual(Volume.objects.count(), 2)
        self.assertEqual(VolumeNode.objects.count(), 4)

    def test_multipath_bare(self):
        """Two hosts, each seeing two block devices via two nodes per block device,
        with no multipath configuration"""
        host1 = synthetic_host('myaddress', storage_resource=True)
        host2 = synthetic_host('myaddress2', storage_resource=True)
        self._start_session_with_data(host1, "multipath_bare.json")
        self._start_session_with_data(host2, "multipath_bare.json")

        self.assertEqual(Volume.objects.count(), 2)
        self.assertEqual(VolumeNode.objects.count(), 8)

    def test_multipath_partitions_HYD_1385(self):
        """A single host, which sees a two-path multipath device that has partitions on it"""
        host1 = synthetic_host('myaddress', storage_resource=True)
        self._start_session_with_data(host1, "HYD-1385.json")

        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 1)
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-2")).count(), 1)

        # And now try it again to make sure that the un-wanted VolumeNodes don't get created on the second pass
        self._start_session_with_data(host1, "HYD-1385.json")
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 1)
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-2")).count(), 1)

    def test_multipath_partitions_HYD_1385_mpath_creation(self):
        """First load a view where there are two nodes that haven't been multipathed together, then
        update with the multipath device in place"""
        host1 = synthetic_host('myaddress', storage_resource=True)

        # There is no multipath
        self._start_session_with_data(host1, "HYD-1385_nompath.json")
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 2)

        # ... now there is, the VolumeNodes should change to reflect that
        self._start_session_with_data(host1, "HYD-1385.json")
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 1)

        # ... and now it's gone again, the VolumeNodes should change back
        self._start_session_with_data(host1, "HYD-1385_nompath.json")
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 2)

    def test_multipath_partitions_HYD_1385_mounted(self):
        """A single host, which sees a two-path multipath device that has partitions on it, one of
        the partitions is mounted via its /dev/mapper/*p1 device node"""
        host1 = synthetic_host('myaddress', storage_resource=True)
        self._start_session_with_data(host1, "HYD-1385_mounted.json")

        # The mounted partition should not be reported as an available volume
        with self.assertRaises(Volume.DoesNotExist):
            Volume.objects.get(label = "MPATH-testdev00-1")

        # The other partition should still be shown
        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-2")).count(), 1)

    def test_HYD_1969(self):
        """Reproducer for HYD-1969, one shared volume is being reported as two separate volumes with the same label."""
        host1 = synthetic_host('mds00', storage_resource=True)
        host2 = synthetic_host('mds01', storage_resource=True)

        self._start_session_with_data(host1, "HYD-1969-mds00.json")
        self._start_session_with_data(host2, "HYD-1969-mds01.json")

        self.assertEqual(Volume.objects.filter(label="3690b11c00006c68d000007ea5158674f").count(), 1)

    def test_HYD_3659(self):
        """
        A removable device with a partition should be culled without an exception.
        """
        # Create entries for the device/partition
        host1 = synthetic_host('mds00', storage_resource=True)
        self._start_session_with_data(host1, "HYD-3659.json")
        self.assertEqual(Volume.objects.count(), 1)

        # Restart the session with no devices (should trigger a cull)
        self._start_session_with_data(host1, "NoDevices.json")
        self.assertEqual(Volume.objects.count(), 0)


class TestBlockDevices(unittest.TestCase):
    """ Verify aggregator output parsed through block_devices matches expected agent output """
    def setUp(self):
        super(TestBlockDevices, self).setUp()

        self.test_root = os.path.join(os.path.dirname(__file__), "fixtures")

        self.load_fixture(u'device_aggregator.text', u'vm7.foo.com')
        self.load_expected(u'agent_plugin.json')

    def load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()

    def load_fixture(self, filename, host_fqdn):
        fixture = compose(json.loads, self.load)(filename)

        with patch('chroma_core.plugins.block_devices.aggregator_get'):
            with patch.dict('chroma_core.plugins.block_devices._data',
                            fixture):
                self.block_devices = get_block_devices(host_fqdn)

    def load_expected(self, filename):
        str_data = self.load(filename)
        self.expected = json.loads(str_data)['result']['linux']

    def test_block_device_nodes_parsing(self):
        result = self.block_devices['devs']

        p = re.compile('\d+:\d+$')

        map(
            lambda x: self.assertTrue(
                all(item in result[x].items() for item in self.expected['devs'][x].items())
            ),
            [mm for mm in self.expected['devs'].keys() if p.match(mm)]
        )

        # todo: ensure we are testing all variants from relevant fixture:
        # - partition
        # - dm-0 linear lvm
        # - dm-2 striped lvm

    def _get_test_pool(self):
        testPool = Mock()
        testPool.name = 'testPool4'
        testPool.state = 'ACTIVE'
        testPool.size = 10670309376
        testPool.vdev = Mock()
        testPool.datasets = []
        testPool.vdev.Root = Mock()
        disk1 = Mock()
        disk1.Disk = Mock()
        disk1.Disk.path = '/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_disk2-part1'
        disk1.Disk.path_id = 'scsi-0QEMU_QEMU_HARDDISK_disk2-part1'
        disk1.Disk.phys_path = 'virtio-pci-0000:00:05.0-scsi-0:0:0:1'
        disk1.Disk.whole_disk = True
        disk1.Disk.is_log = False
        disk4 = Mock()
        disk4.Disk = Mock()
        disk4.Disk.path = '/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_disk4-part1'
        disk4.Disk.path_id = 'scsi-0QEMU_QEMU_HARDDISK_disk4-part1'
        disk4.Disk.phys_path = 'virtio-pci-0000:00:05.0-scsi-0:0:0:3'
        disk4.Disk.whole_disk = True
        disk4.Disk.is_log = False
        testPool.vdev.Root.children = [disk1, disk4]

        return testPool

    def test_get_drive_serials(self):
        self.assertEqual(get_drive_serials(self._get_test_pool(),
                                           self.block_devices['devs']),
                         {u'8:64', u'8:32'})

    # def test_discover_zpools(self):
    #     import ipdb;ipdb.set_trace()
    #     self.assertEqual(discover_zpools(self.block_devices),
    #                      [])

