import json
import os
import re
from mock import patch
from django.utils import unittest
from toolz import compose, curry

from chroma_core.plugins.block_devices import get_block_devices, get_drives, discover_zpools

# from chroma_core.services.plugin_runner import ResourceManager
# from chroma_core.models.host import Volume, VolumeNode
# from chroma_core.models.storage_plugin import StorageResourceRecord
# from tests.unit.chroma_core.helpers import synthetic_host
# from tests.unit.chroma_core.helpers import load_default_profile
# from tests.unit.chroma_core.lib.storage_plugin.helper import load_plugins
# from chroma_core.services.plugin_runner import AgentPluginHandlerCollection
# from tests.unit.lib.iml_unit_test_case import IMLUnitTestCase


#class LinuxPluginTestCase(IMLUnitTestCase):
#    def setUp(self):
#        super(LinuxPluginTestCase, self).setUp()
#
#        self.manager = load_plugins(['linux', 'linux_network'])
#
#        import chroma_core.lib.storage_plugin.manager
#        self.old_manager = chroma_core.lib.storage_plugin.manager.storage_plugin_manager
#        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.manager
#
#        self.resource_manager = ResourceManager()
#
#        load_default_profile()
#
#    def tearDown(self):
#        import chroma_core.lib.storage_plugin.manager
#        chroma_core.lib.storage_plugin.manager.storage_plugin_manager = self.old_manager
#
#    def __init__(self, *args, **kwargs):
#        self._handle_counter = 0
#        super(LinuxPluginTestCase, self).__init__(*args, **kwargs)
#
#    def _make_global_resource(self, plugin_name, class_name, attrs):
#        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
#        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(plugin_name, class_name)
#        resource_record, created = StorageResourceRecord.get_or_create_root(resource_class, resource_class_id, attrs)
#        return resource_record
#
#    def _start_session_with_data(self, host, data_file):
#        # This test impersonates AgentDaemon (load and pass things into a plugin instance)
#        data = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures/%s" % data_file)))
#
#        plugin = AgentPluginHandlerCollection(self.resource_manager).handlers['linux']._create_plugin_instance(host)
#
#        plugin.do_agent_session_start(data['linux'])
#
#    def test_HYD_1269(self):
#        """This test vector caused an exception during Volume generation.
#        It has two block devices with the same serial_80, which should be
#        caught where we scrub out the non-unique IDs that QEMU puts into
#        serial_80."""
#        host = synthetic_host('myaddress', storage_resource=True)
#        self._start_session_with_data(host, "HYD_1269.json")
#        self.assertEqual(Volume.objects.count(), 2)
#
#    def test_HYD_1269_noerror(self):
#        """This test vector is from a different machine at the same time which did not experience the HYD-1272 bug"""
#        host = synthetic_host('myaddress', storage_resource=True)
#        self._start_session_with_data(host, "HYD_1269_noerror.json")
#        # Multiple partitioned devices, sda->sde, 2 partitions each
#        # sda1 is boot, sda2 is a PV
#
#        self.assertEqual(Volume.objects.count(), 8)
#        self.assertEqual(VolumeNode.objects.count(), 8)
#
#    def test_multipath(self):
#        """Two hosts, each seeing two block devices via two nodes per block device,
#        with multipath devices configured correctly"""
#        host1 = synthetic_host('myaddress', storage_resource=True)
#        host2 = synthetic_host('myaddress2', storage_resource=True)
#        self._start_session_with_data(host1, "multipath.json")
#        self._start_session_with_data(host2, "multipath.json")
#
#        self.assertEqual(Volume.objects.count(), 2)
#        self.assertEqual(VolumeNode.objects.count(), 4)
#
#    def test_multipath_bare(self):
#        """Two hosts, each seeing two block devices via two nodes per block device,
#        with no multipath configuration"""
#        host1 = synthetic_host('myaddress', storage_resource=True)
#        host2 = synthetic_host('myaddress2', storage_resource=True)
#        self._start_session_with_data(host1, "multipath_bare.json")
#        self._start_session_with_data(host2, "multipath_bare.json")
#
#        self.assertEqual(Volume.objects.count(), 2)
#        self.assertEqual(VolumeNode.objects.count(), 8)
#
#    def test_multipath_partitions_HYD_1385(self):
#        """A single host, which sees a two-path multipath device that has partitions on it"""
#        host1 = synthetic_host('myaddress', storage_resource=True)
#        self._start_session_with_data(host1, "HYD-1385.json")
#
#        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 1)
#        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-2")).count(), 1)
#
#        # And now try it again to make sure that the un-wanted VolumeNodes don't get created on the second pass
#        self._start_session_with_data(host1, "HYD-1385.json")
#        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 1)
#        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-2")).count(), 1)
#
#    def test_multipath_partitions_HYD_1385_mpath_creation(self):
#        """First load a view where there are two nodes that haven't been multipathed together, then
#        update with the multipath device in place"""
#        host1 = synthetic_host('myaddress', storage_resource=True)
#
#        # There is no multipath
#        self._start_session_with_data(host1, "HYD-1385_nompath.json")
#        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 2)
#
#        # ... now there is, the VolumeNodes should change to reflect that
#        self._start_session_with_data(host1, "HYD-1385.json")
#        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 1)
#
#        # ... and now it's gone again, the VolumeNodes should change back
#        self._start_session_with_data(host1, "HYD-1385_nompath.json")
#        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-1")).count(), 2)
#
#    def test_multipath_partitions_HYD_1385_mounted(self):
#        """A single host, which sees a two-path multipath device that has partitions on it, one of
#        the partitions is mounted via its /dev/mapper/*p1 device node"""
#        host1 = synthetic_host('myaddress', storage_resource=True)
#        self._start_session_with_data(host1, "HYD-1385_mounted.json")
#
#        # The mounted partition should not be reported as an available volume
#        with self.assertRaises(Volume.DoesNotExist):
#            Volume.objects.get(label = "MPATH-testdev00-1")
#
#        # The other partition should still be shown
#        self.assertEqual(VolumeNode.objects.filter(volume = Volume.objects.get(label = "MPATH-testdev00-2")).count(), 1)
#
#    def test_HYD_1969(self):
#        """Reproducer for HYD-1969, one shared volume is being reported as two separate volumes with the same label."""
#        host1 = synthetic_host('mds00', storage_resource=True)
#        host2 = synthetic_host('mds01', storage_resource=True)
#
#        self._start_session_with_data(host1, "HYD-1969-mds00.json")
#        self._start_session_with_data(host2, "HYD-1969-mds01.json")
#
#        self.assertEqual(Volume.objects.filter(label="3690b11c00006c68d000007ea5158674f").count(), 1)
#
#    def test_HYD_3659(self):
#        """
#        A removable device with a partition should be culled without an exception.
#        """
#        # Create entries for the device/partition
#        host1 = synthetic_host('mds00', storage_resource=True)
#        self._start_session_with_data(host1, "HYD-3659.json")
#        self.assertEqual(Volume.objects.count(), 1)
#
#        # Restart the session with no devices (should trigger a cull)
#        self._start_session_with_data(host1, "NoDevices.json")
#        self.assertEqual(Volume.objects.count(), 0)

class TestBase(unittest.TestCase):
    test_host_fqdn = 'vm5.foo.com'

    def setUp(self):
        super(TestBase, self).setUp()
        self.test_root = os.path.join(os.path.dirname(__file__), "fixtures")
        self.addCleanup(patch.stopall)

    def load(self, filename):
        return open(os.path.join(self.test_root, filename)).read()

    def check(self, skip_keys, expect, result, x):
        from toolz import pipe
        from toolz.curried import map as cmap, filter as cfilter

        def cmpval(key):
            expected = expect[x][key]
            actual = result[x][key]
            if type(expected) is dict:
                self.check(skip_keys, expect[x], result[x], key)
            else:
                self.assertEqual(actual, expected,
                                 "item {} ({}) in {} does not match expected ({})".format(key,
                                                                                          actual,
                                                                                          x,
                                                                                          expected))

        pipe(expect[x].keys(),
             cfilter(lambda y: y not in skip_keys),
             cmap(cmpval),
             list)


class TestFormattedBlockDevices(TestBase):
    """ Verify aggregator output parsed through block_devices matches expected agent output """

    def setUp(self):
        super(TestFormattedBlockDevices, self).setUp()

        self.test_root = os.path.join(os.path.dirname(__file__), "fixtures")
        self.fixture = json.loads(self.load(u'device_aggregator_formatted_ldiskfs.text'))
        self.block_devices = self.get_patched_block_devices(dict(self.fixture))
        self.expected = json.loads(self.load(u'agent_plugin_formatted_ldiskfs.json'))['result']['linux']

        self.addCleanup(patch.stopall)

    def get_patched_block_devices(self, fixture):
        with patch('chroma_core.plugins.block_devices.aggregator_get', return_value=fixture):
            return get_block_devices(self.test_host_fqdn)

    def test_block_device_nodes_parsing(self):
        p = re.compile('\d+:\d+$')
        print 'Omitted devices:'
        print (set(self.expected['devs'].keys()) - set([mm for mm in self.expected['devs'].keys() if p.match(mm)]))
        ccheck = curry(self.check, [], self.expected['devs'], self.block_devices['devs'])

        map(
            lambda x: ccheck(x),
            [mm for mm in self.expected['devs'].keys() if p.match(mm)]
        )

        # todo: ensure we are testing all variants from relevant fixture:
        # - partition
        # - dm-0 linear lvm
        # - dm-2 striped lvm

    def test_block_device_local_fs_parsing(self):
        key = 'local_fs'
        map(
            # lambda x: self.assertListEqual(self.expected[key][x],
            #                                self.block_devices[key][x]),
            # fixme: currently the Mountpoint of the local mount is not being provided by block_devices.py
            lambda x: self.assertEqual(self.expected[key][x][1],
                                       self.block_devices[key][x][1]),
            self.expected[key].keys()
        )

    def test_block_device_lvs_parsing(self):
        key = 'lvs'
        # uuid format changed with output now coming from device-scanner
        ccheck = curry(self.check, ['uuid'], self.expected[key], self.block_devices[key])

        map(
            lambda x: ccheck(x),
            self.expected[key].keys()
        )

    def test_block_device_mds_parsing(self):
        key = 'mds'
        ccheck = curry(self.check, [], self.expected[key], self.block_devices[key])

        map(
            lambda x: ccheck(x),
            self.expected[key].keys()
        )

    def test_block_device_vgs_parsing(self):
        key = 'vgs'
        ccheck = curry(self.check, ['uuid'], self.expected[key], self.block_devices[key])

        map(
            lambda x: ccheck(x),
            self.expected[key].keys()
        )


class TestBlockDevices(TestBase):
    """ Verify aggregator output parsed through block_devices matches expected agent output """
    zpool_result = {u'0x0123456789abcdef': {'block_device': 'zfspool:0x0123456789abcdef',
                                            'drives': {u'8:64', u'8:32', u'8:65', u'8:41',
                                                       u'8:73', u'8:33'},
                                            'name': u'testPool4',
                                            'path': u'testPool4',
                                            'size': 10670309376,
                                            'uuid': u'0x0123456789abcdef'}}
    dataset_result = {u'0xDB55C7876B45A0FB-testPool4/f1-OST0000': {'block_device':
                                                                   'zfsset:0xDB55C7876B45A0FB-testPool4/f1-OST0000',
                                                                   'drives': {u'8:64', u'8:32', u'8:65', u'8:41',
                                                                              u'8:73', u'8:33'},
                                                                   'name': u'testPool4/f1-OST0000',
                                                                   'path': u'testPool4/f1-OST0000',
                                                                   'size': 0,
                                                                   'uuid': u'0xDB55C7876B45A0FB-testPool4/f1-OST0000'}}

    def setUp(self):
        super(TestBlockDevices, self).setUp()

        self.fixture = compose(json.loads, self.load)(u'device_aggregator.text')
        self.block_devices = self.get_patched_block_devices(dict(self.fixture))
        self.expected = json.loads(self.load(u'agent_plugin.json'))['result']['linux']

    def get_patched_block_devices(self, fixture):
        with patch('chroma_core.plugins.block_devices.aggregator_get', return_value=fixture):
            return get_block_devices(self.test_host_fqdn)

    def patch_zed_data(self, fixture, host_fqdn, pools=None, zfs=None, props=None):
        """ overwrite with supplied structures or if None supplied in parameters, copy from existing host """
        # take copy of fixture so we return a new one and leave the original untouched
        fixture = dict(fixture)

        # copy existing host data if simulating new host
        host_data = json.loads(fixture.setdefault(host_fqdn,
                                                  fixture[self.test_host_fqdn]))
        host_data['zed'] = {'zpools': pools if pools is not None else host_data['zed']['zpools'],
                            'zfs': zfs if zfs is not None else host_data['zed']['zfs'],
                            'props': props if props is not None else host_data['zed']['props']}

        fixture[host_fqdn] = json.dumps(host_data)

        return fixture

    @staticmethod
    def get_test_pool(state='ACTIVE'):
        return {
          "guid": '0x0123456789abcdef',
          "name": 'testPool4',
          "state": state,
          "size": 10670309376,
          "datasets": [],
          "vdev": {'Root': {'children': [
            {
              "Disk": {
                "path": '/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_disk2-part1',
                "path_id": 'scsi-0QEMU_QEMU_HARDDISK_disk2-part1',
                "phys_path": 'virtio-pci-0000:00:05.0-scsi-0:0:0:1',
                "whole_disk": True,
                "is_log": False
              }
            },
            {
              "Disk": {
                "path": '/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_disk4-part1',
                "path_id": 'scsi-0QEMU_QEMU_HARDDISK_disk4-part1',
                "phys_path": 'virtio-pci-0000:00:05.0-scsi-0:0:0:3',
                "whole_disk": True,
                "is_log": False
              }
            }]
          }}
        }

    def test_block_device_nodes_parsing(self):
        p = re.compile('\d+:\d+$')
        ccheck = curry(self.check, [], self.expected['devs'], self.block_devices['devs'])

        map(
            lambda x: ccheck(x),
            [mm for mm in self.expected['devs'].keys() if p.match(mm)]
        )

        # todo: ensure we are testing all variants from relevant fixture:
        # - partition
        # - dm-0 linear lvm
        # - dm-2 striped lvm

    def test_get_drives(self):
        self.assertEqual(get_drives([child['Disk'] for child in self.get_test_pool()['vdev']['Root']['children']],
                                    self.block_devices['devs']),
                         {u'8:64', u'8:32', u'8:65', u'8:41', u'8:73', u'8:33'})

    def test_discover_zpools(self):
        """ verify block devices are unchanged when no accessible pools exist on other hosts """
        original_block_devices = dict(self.block_devices)
        self.assertEqual(discover_zpools(self.block_devices, self.fixture),
                         original_block_devices)

    def test_discover_zpools_unavailable_other(self):
        """ verify block devices are unchanged when locally active pool exists unavailable on other hosts """
        fixture = self.patch_zed_data(dict(self.fixture),
                                      self.test_host_fqdn,
                                      {'0x0123456789abcdef': self.get_test_pool('ACTIVE')},
                                      {},
                                      {})

        original_block_devices = self.get_patched_block_devices(dict(fixture))

        fixture = self.patch_zed_data(dict(fixture),
                                      'vm6.foo.com',
                                      {'0x0123456789abcdef': self.get_test_pool('UNAVAIL')},
                                      {},
                                      {})

        self.assertEqual(self.get_patched_block_devices(fixture), original_block_devices)

    def test_discover_zpools_exported_other(self):
        """ verify block devices are unchanged when locally active pool exists exported on other hosts """
        fixture = self.patch_zed_data(dict(self.fixture),
                                      self.test_host_fqdn,
                                      {'0x0123456789abcdef': self.get_test_pool('ACTIVE')},
                                      {},
                                      {})

        original_block_devices = self.get_patched_block_devices(dict(fixture))

        fixture = self.patch_zed_data(dict(fixture),
                                      'vm6.foo.com',
                                      {'0x0123456789abcdef': self.get_test_pool('EXPORTED')},
                                      {},
                                      {})

        self.assertEqual(self.get_patched_block_devices(fixture), original_block_devices)

    def test_discover_zpools_unknown(self):
        """ verify block devices are updated when accessible but unknown pools are active on other hosts """
        # remove pool and zfs data from fixture
        fixture = self.patch_zed_data(self.fixture,
                                      self.test_host_fqdn,
                                      {},
                                      {},
                                      {})

        block_devices = self.get_patched_block_devices(dict(fixture))

        # no pools or datasets should be reported after processing
        block_devices = discover_zpools(block_devices, fixture)
        [self.assertEqual(block_devices[key], {}) for key in ['zfspools', 'zfsdatasets']]

        # add pool and zfs data to fixture for another host
        fixture = self.patch_zed_data(fixture,
                                      'vm6.foo.com',
                                      {'0x0123456789abcdef': self.get_test_pool('ACTIVE')},
                                      {},
                                      {})

        block_devices = self.get_patched_block_devices(fixture)

        # new pool on other host should be reported after processing, because drives are shared
        self.assertEqual(block_devices['zfspools'], self.zpool_result)

    def test_discover_dataset_unknown(self):
        """ verify block devices are updated when accessible but unknown datasets are active on other hosts """
        # copy pool and zfs data to fixture for another host
        fixture = self.patch_zed_data(self.fixture,
                                      'vm6.foo.com')

        # remove pool and zfs data from fixture for current host
        fixture = self.patch_zed_data(fixture,
                                      self.test_host_fqdn,
                                      {},
                                      {},
                                      {})

        block_devices = self.get_patched_block_devices(fixture)

        # datasets should be reported after processing
        self.assertEqual(block_devices['zfspools'], {})
        self.assertEqual(block_devices['zfsdatasets'], self.dataset_result)

    def test_discover_zpools_both_active(self):
        """ verify exception thrown when accessible active pools are active on other hosts """
        fixture = self.patch_zed_data(self.fixture,
                                      self.test_host_fqdn,
                                      {'0x0123456789abcdef': self.get_test_pool('ACTIVE')},
                                      {},
                                      {})

        block_devices = self.get_patched_block_devices(fixture)

        fixture = self.patch_zed_data(self.fixture,
                                      'vm6.foo.com',
                                      {'0x0123456789abcdef': self.get_test_pool('ACTIVE')},
                                      {},
                                      {})

        with self.assertRaises(RuntimeError):
            discover_zpools(block_devices, fixture)

    def test_ignore_exported_zpools(self):
        """ verify exported pools are not reported """
        fixture = self.patch_zed_data(self.fixture,
                                      self.test_host_fqdn,
                                      {'0x0123456789abcdef': self.get_test_pool('EXPORTED')},
                                      {},
                                      {})

        block_devices = self.get_patched_block_devices(fixture)

        self.assertEqual(block_devices['zfspools'], {})
        self.assertEqual(block_devices['zfsdatasets'], {})

    def test_ignore_other_exported_zpools(self):
        """ verify elsewhere exported pools are not reported """
        fixture = self.patch_zed_data(self.fixture,
                                      self.test_host_fqdn,
                                      {},
                                      {},
                                      {})

        fixture = self.patch_zed_data(fixture,
                                      'vm6.foo.com',
                                      {'0x0123456789abcdef': self.get_test_pool('EXPORTED')},
                                      {},
                                      {})

        block_devices = self.get_patched_block_devices(fixture)

        self.assertEqual(block_devices['zfspools'], {})
        self.assertEqual(block_devices['zfsdatasets'], {})
