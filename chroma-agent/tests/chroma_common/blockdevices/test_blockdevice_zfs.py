import glob
import mock

from os import path
from chroma_agent.chroma_common.blockdevices.blockdevice_zfs import BlockDeviceZfs
from chroma_agent.chroma_common.lib.agent_rpc import agent_result_ok
from tests.chroma_common.blockdevices.blockdevice_base_tests import BaseTestBD
from tests.data.chroma_common import example_data
from tests.command_capture_testcase import CommandCaptureCommand


class TestBlockDeviceZFS(BaseTestBD.BaseTestBlockDevice):
    pool_name = 'zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333'
    dataset_path = '/'.join([pool_name, 'ost_index0'])

    def setUp(self):
        super(TestBlockDeviceZFS, self).setUp()

        self.patch_init_modules = mock.patch.object(BlockDeviceZfs, '_initialize_modules')
        self.patch_init_modules.start()

        self.blockdevice = BlockDeviceZfs('zfs', self.pool_name)

        self.addCleanup(mock.patch.stopall)

    def test_initialize_modules(self):
        self.patch_init_modules.stop()

        self.add_commands(CommandCaptureCommand(('modprobe', 'osd_zfs')),
                          CommandCaptureCommand(('modprobe', 'zfs')))

        self.blockdevice._initialize_modules()
        self.assertTrue(self.blockdevice._modules_initialized)

        self.assertRanAllCommandsInOrder()

    def test_filesystem_type_unoccupied(self):
        # this should be called with device_path referencing a zpool
        self.add_command(('zfs', 'list', '-H', '-o', 'name', '-r', self.blockdevice._device_path),
                         stdout=self.blockdevice._device_path)

        self.assertEqual(None, self.blockdevice.filesystem_type)
        self.assertRanAllCommandsInOrder()

    def test_filesystem_type_occupied(self):
        # this should be called with device_path referencing a zpool
        self.add_command(('zfs', 'list', '-H', '-o', 'name', '-r', self.blockdevice._device_path),
                         stdout='%(pool)s\n%(pool)s/dataset_1' % {'pool': self.blockdevice._device_path})

        self.assertEqual('zfs', self.blockdevice.filesystem_type)
        self.assertRanAllCommandsInOrder()

    def test_filesystem_info_unoccupied(self):
        # this should be called with device_path referencing a zpool
        self.add_command(('zfs', 'list', '-H', '-o', 'name', '-r', self.blockdevice._device_path),
                         stdout=self.blockdevice._device_path)

        self.assertEqual(None, self.blockdevice.filesystem_info)
        self.assertRanAllCommandsInOrder()

    def test_filesystem_info_occupied(self):
        # this should be called with device_path referencing a zpool
        self.add_command(('zfs', 'list', '-H', '-o', 'name', '-r', self.blockdevice._device_path),
                         stdout='%(pool)s\n%(pool)s/dataset_1' % {'pool': self.blockdevice._device_path})

        self.assertEqual("Dataset 'dataset_1' found on zpool '%s'" %
                         self.blockdevice._device_path, self.blockdevice.filesystem_info)
        self.assertRanAllCommandsInOrder()

    def test_filesystem_info_occupied_multiple(self):
        # this should be called with device_path referencing a zpool
        self.add_command(('zfs', 'list', '-H', '-o', 'name', '-r', self.blockdevice._device_path),
                         stdout='%(pool)s\n%(pool)s/dataset_1\n%(pool)s/dataset_2' % {'pool':
                                                                                      self.blockdevice._device_path})

        self.assertEqual("Datasets 'dataset_1,dataset_2' found on zpool '%s'" %
                         self.blockdevice._device_path, self.blockdevice.filesystem_info)
        self.assertRanAllCommandsInOrder()

    def test_uuid(self):
        self.add_command(('zfs', 'get', '-H', '-o', 'value', 'guid', self.blockdevice._device_path),
                         stdout='169883839435093209\n')

        self.assertEqual('169883839435093209', self.blockdevice.uuid)
        self.assertRanAllCommandsInOrder()

    def test_preferred_fstype(self):
        self.assertEqual('zfs', self.blockdevice.preferred_fstype)

    def test_device_type(self):
        self.assertEqual('zfs', self.blockdevice.device_type)

    def test_device_path(self):
        self.assertEqual(self.pool_name, self.blockdevice._device_path)

    def test_mgs_targets(self):
        self.assertEqual({}, self.blockdevice.mgs_targets(None))

    def test_import_success_non_pacemaker(self):
        self.blockdevice = BlockDeviceZfs('zfs', self.dataset_path)

        self.add_commands(CommandCaptureCommand(('zpool', 'list', self.pool_name), rc=1),
                          CommandCaptureCommand(('zpool', 'import', self.pool_name)),
                          CommandCaptureCommand(('zfs', 'get', '-Hp', '-o', 'property,value', 'all', self.pool_name),
                                                stdout='compressratio\t1.00x\n'
                                                       'mounted\tyes\n'
                                                       'quota\t0\n'
                                                       'reservation\t0'))

        self.assertIsNone(self.blockdevice.import_(False))
        self.assertRanAllCommandsInOrder()

    def test_import_existing_readonly(self):
        self.blockdevice = BlockDeviceZfs('zfs', self.dataset_path)

        self.add_commands(CommandCaptureCommand(('zpool', 'list', self.pool_name), executions_remaining=1),
                          CommandCaptureCommand(('zfs', 'get', '-Hp', '-o', 'property,value', 'all', self.pool_name),
                                                stdout='compressratio\t1.00x\n'
                                                       'mounted\tyes\n'
                                                       'quota\t0\n'
                                                       'readonly\ton',
                                                executions_remaining=1),
                          CommandCaptureCommand(('zpool', 'list', self.pool_name),
                                                executions_remaining=1),
                          CommandCaptureCommand(('zpool', 'export', self.pool_name)),
                          CommandCaptureCommand(('zpool', 'list', self.pool_name), rc=1),
                          CommandCaptureCommand(('zpool', 'import', self.pool_name)),
                          CommandCaptureCommand(('zfs', 'get', '-Hp', '-o', 'property,value', 'all', self.pool_name),
                                                stdout='compressratio\t1.00x\n'
                                                       'mounted\tyes\n'
                                                       'quota\t0'))

        self.assertIsNone(self.blockdevice.import_(False))
        self.assertRanAllCommandsInOrder()

    def test_import_success_with_pacemaker(self):
        self.blockdevice = BlockDeviceZfs('zfs', self.dataset_path)

        self.add_commands(CommandCaptureCommand(('zpool', 'list', self.blockdevice._device_path.split('/')[0]), rc=1),
                          CommandCaptureCommand(('zpool', 'import', '-f', self.blockdevice._device_path.split('/')[0])),
                          CommandCaptureCommand(('zfs', 'get', '-Hp', '-o', 'property,value', 'all', self.pool_name),
                                                stdout='compressratio\t1.00x\n'
                                                       'mounted\tyes\n'
                                                       'quota\t0\n'
                                                       'reservation\t0'))

        self.assertIsNone(self.blockdevice.import_(True))
        self.assertRanAllCommandsInOrder()

    def test_import_existing_non_pacemaker(self):
        self.blockdevice = BlockDeviceZfs('zfs', self.dataset_path)

        self.add_commands(CommandCaptureCommand(('zpool', 'list', self.pool_name)),
                          CommandCaptureCommand(('zfs', 'get', '-Hp', '-o', 'property,value', 'all', self.pool_name),
                                                stdout='compressratio\t1.00x\n'
                                                       'mounted\tyes\n'
                                                       'quota\t0\n'
                                                       'reservation\t0'))

        self.assertIsNone(self.blockdevice.import_(False))
        self.assertRanAllCommandsInOrder()

    def test_import_existing_with_pacemaker(self):
        self.test_import_existing_non_pacemaker()

    def test_export_success(self):
        self.blockdevice = BlockDeviceZfs('zfs', self.dataset_path)

        self.add_command(('zpool', 'list', self.pool_name))
        self.add_command(('zpool', 'export', self.pool_name))

        self.assertIsNone(self.blockdevice.export())
        self.assertRanAllCommandsInOrder()

    def test_export_missing(self):
        self.blockdevice = BlockDeviceZfs('zfs', self.dataset_path)

        self.add_command(('zpool', 'list', self.pool_name), rc=1)

        self.assertIsNone(self.blockdevice.export())
        self.assertRanAllCommandsInOrder()

    def test_property_values(self):
        self.blockdevice = BlockDeviceZfs('zfs', self.dataset_path)

        self.add_command(('zfs', 'get', '-Hp', '-o', 'property,value', 'all', self.blockdevice._device_path),
                         stdout=example_data.zfs_example_properties)

        zfs_properties = self.blockdevice.zfs_properties(False)

        self.assertEqual(zfs_properties['lustre:fsname'], 'efs')
        self.assertEqual(zfs_properties['lustre:svname'], 'efs-MDT0000')
        self.assertEqual(zfs_properties['lustre:flags'], '37')
        self.assertRanAllCommandsInOrder()

    def test_targets(self):
        self.blockdevice = BlockDeviceZfs('zfs', self.dataset_path)

        self.add_command(('zfs', 'get', '-Hp', '-o', 'property,value', 'all', self.blockdevice._device_path),
                         stdout=example_data.zfs_example_properties)

        target_info = self.blockdevice.targets(None, None, None)

        self.assertIn('efs-MDT0000', target_info.names)
        self.assertEqual(target_info.params['fsname'], ['efs'])
        self.assertEqual(target_info.params['svname'], ['efs-MDT0000'])
        self.assertEqual(target_info.params['flags'], ['37'])
        self.assertRanAllCommandsInOrder()

    def test_purge_filesystem_information(self):
        self.blockdevice = BlockDeviceZfs('zfs', self.dataset_path)
        device_path = self.blockdevice._device_path

        self.add_commands(CommandCaptureCommand(('zfs', 'canmount=on', device_path)),
                          CommandCaptureCommand(('zfs', 'mount', device_path)),
                          CommandCaptureCommand(('rm', 'testfs-a')),
                          CommandCaptureCommand(('rm', 'testfs-b')),
                          CommandCaptureCommand(('zfs', 'unmount', device_path)),
                          CommandCaptureCommand(('zfs', 'canmount=off', device_path)))

        with mock.patch.object(glob, 'glob', return_value=['testfs-a', 'testfs-b']) as mock_glob:
            result = self.blockdevice.purge_filesystem_configuration('testfs', None)

        mock_glob.assert_called_once_with('/%s/CONFIGS/%s-*' % (device_path, 'testfs'))

        self.assertEqual(result, None)
        self.assertRanAllCommandsInOrder()

    def test_initialise_driver(self):
        self.add_commands(CommandCaptureCommand(('genhostid',)))

        with mock.patch.object(path, 'isfile', return_value=False):
            result = BlockDeviceZfs.initialise_driver()

        self.assertEqual(result, agent_result_ok)
        self.assertRanAllCommandsInOrder()

    def test_initialise_driver_file_exists(self):
        with mock.patch.object(path, 'isfile', return_value=True):
            result = BlockDeviceZfs.initialise_driver()

        self.assertEqual(result, agent_result_ok)
        self.assertRanAllCommandsInOrder()

    def test_initialise_driver_fail(self):
        self.add_commands(CommandCaptureCommand(('genhostid',), rc=1, stderr='sample error text'))

        with mock.patch.object(path, 'isfile', return_value=False):
            result = BlockDeviceZfs.initialise_driver()

        self.assertIn('sample error text', result['error'])
        self.assertRanAllCommandsInOrder()
