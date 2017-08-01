import mock

from chroma_agent.action_plugins import manage_targets
from chroma_agent.chroma_common.blockdevices.blockdevice import BlockDevice
from chroma_agent.chroma_common.blockdevices.blockdevice_zfs import BlockDeviceZfs
from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand

from django.utils import unittest


class TestWriteconfTarget(CommandCaptureTestCase):
    def test_mdt_tunefs(self):
        self.add_command(('tunefs.lustre', '--mdt', '/dev/foo'))

        manage_targets.writeconf_target(device='/dev/foo',
                                        target_types=['mdt'])
        self.assertRanAllCommands()

    def test_mgs_tunefs(self):
        self.add_command(("tunefs.lustre", "--mgs", "/dev/foo"))

        manage_targets.writeconf_target(device='/dev/foo',
                                        target_types=['mgs'])
        self.assertRanAllCommands()

    def test_ost_tunefs(self):
        self.add_command(("tunefs.lustre", "--ost", "/dev/foo"))

        manage_targets.writeconf_target(device='/dev/foo',
                                        target_types=['ost'])
        self.assertRanAllCommands()

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        self.add_command(("tunefs.lustre", "--mgs", "--mdt", "/dev/foo"))

        manage_targets.writeconf_target(device='/dev/foo',
                                        target_types=['mgs', 'mdt'])
        self.assertRanAllCommands()

    def test_dict_opts(self):
        self.add_command(("tunefs.lustre", "--param", "foo=bar", "--param", "baz=qux thud", "/dev/foo"))

        manage_targets.writeconf_target(device='/dev/foo',
                                        param={'foo': 'bar', 'baz': 'qux thud'})
        self.assertRanAllCommands()

    def test_flag_opts(self):
        self.add_command(("tunefs.lustre", "--dryrun", "/dev/foo"))

        manage_targets.writeconf_target(device='/dev/foo',
                                        dryrun=True)
        self.assertRanAllCommands()

    def test_other_opts(self):
        self.add_command(("tunefs.lustre", "--index=42", "--mountfsoptions=-x 30 --y --z=83", "/dev/foo"))

        manage_targets.writeconf_target(device='/dev/foo',
                                        index='42', mountfsoptions='-x 30 --y --z=83')
        self.assertRanAllCommands()

    def test_mgsnode_multiple_nids(self):
        self.add_command(("tunefs.lustre", "--erase-params", "--mgsnode=1.2.3.4@tcp,4.3.2.1@tcp1", "--mgsnode=1.2.3.5@tcp0,4.3.2.2@tcp1", "--writeconf", "/dev/foo"))

        manage_targets.writeconf_target(device='/dev/foo',
                                        writeconf = True,
                                        erase_params = True,
                                        mgsnode = [['1.2.3.4@tcp', '4.3.2.1@tcp1'], ['1.2.3.5@tcp0', '4.3.2.2@tcp1']])
        self.assertRanAllCommands()

    def test_unknown_opt(self):
        self.assertRaises(TypeError, manage_targets.writeconf_target, unknown='whatever')


class TestFormatTarget(CommandCaptureTestCase):
    block_device_list = [BlockDevice('linux', '/dev/foo'),
                         BlockDevice('zfs', 'lustre1')]

    def setUp(self):
        super(TestFormatTarget, self).setUp()

        mock.patch('chroma_agent.chroma_common.blockdevices.blockdevice_zfs.ZfsDevice.lock_pool').start()
        mock.patch('chroma_agent.chroma_common.blockdevices.blockdevice_zfs.ZfsDevice.unlock_pool').start()

        self.addCleanup(mock.patch.stopall)

    def _mkfs_path(self, block_device, target_name):
        """ The mkfs path could be different for different block_device types. Today it isn't but it was when this
        method was added and so rather than remove the method I've made it return the same value for both cases and
        perhaps in the future it will be called into use again
        """
        if block_device.device_type == 'linux':
            return block_device.device_path
        elif block_device.device_type == 'zfs':
            return "%s/%s" % (block_device.device_path, target_name)
            # TODO: when BlockDevice and FileSystem merge
            # return block_device.mount_path(target_name)

        assert "Unknown device type %s" % block_device.device_type

    def _setup_run_exceptions(self, block_device, run_args):
        self._run_command = CommandCaptureCommand(tuple(filter(None, run_args)))

        self.add_commands(CommandCaptureCommand(("zpool", "set", "failmode=panic", "lustre1")),
                          CommandCaptureCommand(("dumpe2fs", "-h", "/dev/foo"),
                                                stdout="Inode size: 1024\nInode count: 1024\n"),
                          CommandCaptureCommand(("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/foo"),
                                                stdout="%s\n" % block_device.preferred_fstype),
                          CommandCaptureCommand(("blkid", "-p", "-o", "value", "-s", "UUID", "/dev/foo"),
                                                stdout="123456789\n"),
                          CommandCaptureCommand(("zpool", "list", "-H", "-o", "name"),
                                                stdout='lustre1'),
                          CommandCaptureCommand(("zfs", "get", "-H", "-o", "value", "guid", "lustre1/OST0000"),
                                                stdout="9845118046416187754"),
                          CommandCaptureCommand(("zfs", "get", "-H", "-o", "value", "guid", "lustre1/MDT0000"),
                                                stdout="9845118046416187755"),
                          CommandCaptureCommand(("zfs", "get", "-H", "-o", "value", "guid", "lustre1/MGS0000"),
                                                stdout="9845118046416187756"),
                          CommandCaptureCommand(("zfs", "list", "-H", "-o", "name", "-r", "lustre1")),
                          CommandCaptureCommand(("modprobe", "%s" % block_device.preferred_fstype)),
                          CommandCaptureCommand(("modprobe", "osd_%s" % block_device.preferred_fstype)),
                          self._run_command)

    def test_mdt_mkfs(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--mdt",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        '--mkfsoptions="mountpoint=none"' if block_device.device_type == 'zfs' else '',
                                        self._mkfs_path(block_device, "MDT0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         device_type = block_device.device_type,
                                         target_name = "MDT0000",
                                         backfstype = block_device.preferred_fstype,
                                         target_types=['mdt'])

            self.assertRanCommand(self._run_command)

    def test_mgs_mkfs(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--mgs",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        '--mkfsoptions="mountpoint=none"' if block_device.device_type == 'zfs' else '',
                                        self._mkfs_path(block_device, "MGS0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         device_type = block_device.device_type,
                                         target_name = "MGS0000",
                                         backfstype = block_device.preferred_fstype,
                                         target_types=['mgs'])

            self.assertRanCommand(self._run_command)

    def test_ost_mkfs(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--ost",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        '--mkfsoptions="mountpoint=none"' if block_device.device_type == 'zfs' else '',
                                        self._mkfs_path(block_device, "MDT0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         device_type = block_device.device_type,
                                         target_name = "MDT0000",
                                         backfstype = block_device.preferred_fstype,
                                         target_types=['ost'])

            self.assertRanCommand(self._run_command)

    def test_single_mgs_one_nid(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--ost",
                                        "--mgsnode=1.2.3.4@tcp",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        '--mkfsoptions="mountpoint=none"' if block_device.device_type == 'zfs' else '',
                                        self._mkfs_path(block_device, "OST0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         device_type = block_device.device_type,
                                         target_name = "OST0000",
                                         backfstype = block_device.preferred_fstype,
                                         target_types=['ost'],
                                         mgsnode=[['1.2.3.4@tcp']])

            self.assertRanCommand(self._run_command)

    def test_mgs_pair_one_nid(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre", "--ost",
                                        "--mgsnode=1.2.3.4@tcp",
                                        "--mgsnode=1.2.3.5@tcp",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        '--mkfsoptions="mountpoint=none"' if block_device.device_type == 'zfs' else '',
                                        self._mkfs_path(block_device, "OST0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         target_types=['ost'],
                                         target_name = "OST0000",
                                         backfstype = block_device.preferred_fstype,
                                         device_type = block_device.device_type,
                                         mgsnode=[['1.2.3.4@tcp'], ['1.2.3.5@tcp']])

            self.assertRanCommand(self._run_command)

    def test_single_mgs_multiple_nids(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--ost",
                                        "--mgsnode=1.2.3.4@tcp0,4.3.2.1@tcp1",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        '--mkfsoptions="mountpoint=none"' if block_device.device_type == 'zfs' else '',
                                        self._mkfs_path(block_device, "OST0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         target_types=['ost'],
                                         target_name = "OST0000",
                                         backfstype = block_device.preferred_fstype,
                                         device_type = block_device.device_type,
                                         mgsnode=[['1.2.3.4@tcp0', '4.3.2.1@tcp1']])

            self.assertRanCommand(self._run_command)

    def test_mgs_pair_multiple_nids(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--ost",
                                        "--mgsnode=1.2.3.4@tcp0,4.3.2.1@tcp1",
                                        "--mgsnode=1.2.3.5@tcp0,4.3.2.2@tcp1",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        '--mkfsoptions="mountpoint=none"' if block_device.device_type == 'zfs' else '',
                                        self._mkfs_path(block_device, "OST0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         target_name = "OST0000",
                                         backfstype = block_device.preferred_fstype,
                                         target_types =['ost'],
                                         device_type = block_device.device_type,
                                         mgsnode=[['1.2.3.4@tcp0', '4.3.2.1@tcp1'], ['1.2.3.5@tcp0', '4.3.2.2@tcp1']])

            self.assertRanCommand(self._run_command)

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--mgs",
                                        "--mdt", "--backfstype=%s" % block_device.preferred_fstype,
                                        '--mkfsoptions="mountpoint=none"' if block_device.device_type == 'zfs' else '',
                                        self._mkfs_path(block_device, "MGS0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         device_type = block_device.device_type,
                                         target_name = "MGS0000",
                                         backfstype = block_device.preferred_fstype,
                                         target_types=['mgs', 'mdt'])

            self.assertRanCommand(self._run_command)

    def test_dict_opts(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--param",
                                        "foo=bar",
                                        "--param",
                                        "baz=qux thud",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        '--mkfsoptions="mountpoint=none"' if block_device.device_type == 'zfs' else '',
                                        self._mkfs_path(block_device, "MGS0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         device_type = block_device.device_type,
                                         target_name = "MGS0000",
                                         backfstype = block_device.preferred_fstype,
                                         param={'foo': 'bar', 'baz': 'qux thud'})

            self.assertRanCommand(self._run_command)

    def test_flag_opts(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--dryrun",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        '--mkfsoptions="mountpoint=none"' if block_device.device_type == 'zfs' else '',
                                        self._mkfs_path(block_device, "MGS0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         device_type = block_device.device_type,
                                         target_name = "MGS0000",
                                         backfstype = block_device.preferred_fstype,
                                         dryrun=True)

            self.assertRanCommand(self._run_command)

    def test_zero_opt(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--index=0",
                                        '--mkfsoptions=%s' % ('-x 30 --y --z=83' if block_device.device_type == 'linux' else '"mountpoint=none"'),
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        self._mkfs_path(block_device, "MGS0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         device_type = block_device.device_type,
                                         target_name = "MGS0000",
                                         backfstype = block_device.preferred_fstype,
                                         index=0,
                                         mkfsoptions='-x 30 --y --z=83' if block_device.device_type == 'linux' else '"mountpoint=none"')
            self.assertRanCommand(self._run_command)

    def test_other_opts(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--index=42",
                                        '--mkfsoptions=%s' % ('-x 30 --y --z=83' if block_device.device_type == 'linux' else '"mountpoint=none"'),
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        self._mkfs_path(block_device, "MGS0000")))

            manage_targets.format_target(device = block_device.device_path,
                                         device_type = block_device.device_type,
                                         target_name = "MGS0000",
                                         backfstype = block_device.preferred_fstype,
                                         index=42,
                                         mkfsoptions='-x 30 --y --z=83' if block_device.device_type == 'linux' else '"mountpoint=none"')

            self.assertRanCommand(self._run_command)

    def test_unknown_opt(self):
        self.assertRaises(TypeError, manage_targets.format_target, unknown='whatever')


class TestXMLParsing(unittest.TestCase):
    xml_example = """<primitive class="ocf" provider="chroma" type="Target" id="MGS_a3903a">
  <meta_attributes id="MGS_a3903a-meta_attributes">
    <nvpair name="target-role" id="MGS_a3903a-meta_attributes-target-role" value="Started"/>
  </meta_attributes>
  <operations id="MGS_a3903a-operations">
    <op id="MGS_a3903a-monitor-120" interval="120" name="monitor" timeout="60"/>
    <op id="MGS_a3903a-start-0" interval="0" name="start" timeout="300"/>
    <op id="MGS_a3903a-stop-0" interval="0" name="stop" timeout="300"/>
  </operations>
  <instance_attributes id="MGS_a3903a-instance_attributes">
    <nvpair id="MGS_a3903a-instance_attributes-target" name="target" value="c2890397-e0a2-4759-8f4e-df5ed64e1518"/>
  </instance_attributes>
</primitive>
"""

    def test_get_nvpairid_from_xml(self):
        self.assertEqual('c2890397-e0a2-4759-8f4e-df5ed64e1518', manage_targets._get_nvpairid_from_xml(self.xml_example))


class TestCheckBlockDevice(CommandCaptureTestCase):
    def setUp(self):
        super(TestCheckBlockDevice, self).setUp()

        mock.patch('chroma_agent.chroma_common.blockdevices.blockdevice_zfs.ZfsDevice.lock_pool').start()
        mock.patch('chroma_agent.chroma_common.blockdevices.blockdevice_zfs.ZfsDevice.unlock_pool').start()

    def test_occupied_device_ldiskfs(self):
        self.add_commands(CommandCaptureCommand(("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/sdb"), stdout="ext4\n"))

        result = manage_targets.check_block_device('/dev/sdb', 'linux')
        self.assertEqual(result['result'], 'ext4')
        self.assertRanAllCommands()

    def test_mbr_device_ldiskfs(self):
        self.add_commands(CommandCaptureCommand(("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/sdb"), stdout="\n"))

        result = manage_targets.check_block_device('/dev/sdb', 'linux')
        self.assertEqual(result['result'], None)
        self.assertRanAllCommands()

    def test_empty_device_ldiskfs(self):
        self.add_commands(CommandCaptureCommand(("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/sdb"), rc=2))

        result = manage_targets.check_block_device('/dev/sdb', 'linux')
        self.assertEqual(result['result'], None)
        self.assertRanAllCommands()

    def test_occupied_device_zfs(self):
        self.add_command(("zfs", "list", "-H", "-o", "name", "-r", "pool1"), stdout="pool1\npool1/dataset_1\n")

        result = manage_targets.check_block_device("pool1", "zfs")
        self.assertEqual(result['result'], 'zfs')
        self.assertRanAllCommands()

    def test_empty_device_zfs(self):
        self.add_command(("zfs", "list", "-H", "-o", "name", "-r", "pool1"), stdout="pool1\n")

        result = manage_targets.check_block_device("pool1", "zfs")
        self.assertEqual(result['result'], None)
        self.assertRanAllCommands()

    def test_dataset_device_zfs(self):
        self.add_command(("zfs", "list", "-H", "-o", "name", "-r", "pool1"), stdout="pool1\npool1/dataset_1\n")

        result = manage_targets.check_block_device("pool1/dataset_1", "zfs")
        self.assertEqual(result['result'], 'zfs')
        self.assertRanAllCommands()

    def test_nonexistent_dataset_device_zfs(self):
        self.add_command(("zfs", "list", "-H", "-o", "name", "-r", "pool1"), stdout="pool1\n")

        result = manage_targets.check_block_device("pool1/dataset_1", "zfs")
        self.assertEqual(result['result'], None)
        self.assertRanAllCommands()


class TestCheckImportExport(CommandCaptureTestCase):
    """
    Test that the correct blockdevice methods are called, implementation of methods tested in
    test_blockdevice_zfs therefore don't repeat command capturing here
    """
    zpool = 'zpool'
    zpool_dataset = '%s/dataset' % zpool

    def setUp(self):
        super(TestCheckImportExport, self).setUp()

        self.patch_init_modules = mock.patch.object(BlockDeviceZfs, '_initialize_modules')
        self.patch_init_modules.start()
        self.mock_import_ = mock.Mock(return_value=None)
        self.patch_import_ = mock.patch.object(BlockDeviceZfs, 'import_', self.mock_import_)
        self.patch_import_.start()
        self.mock_export = mock.Mock(return_value=None)
        self.patch_export = mock.patch.object(BlockDeviceZfs, 'export', self.mock_export)
        self.patch_export.start()

        self.addCleanup(mock.patch.stopall)

    def test_import_device_ldiskfs(self):
        for with_pacemaker in [True, False]:
            self.assertAgentOK(manage_targets.import_target('linux', '/dev/sdb', with_pacemaker))
            self.assertRanAllCommandsInOrder()

    def test_export_device_ldiskfs(self):
        self.assertAgentOK(manage_targets.export_target('linux', '/dev/sdb'))
        self.assertRanAllCommandsInOrder()

    def test_import_device_zfs(self):
        for with_pacemaker in [True, False]:
            self.mock_import_.reset_mock()
            self.assertAgentOK(manage_targets.import_target('zfs', self.zpool_dataset, with_pacemaker))
            self.mock_import_.assert_called_once_with(with_pacemaker)

    def test_export_device_zfs(self):
        self.assertAgentOK(manage_targets.export_target('zfs', self.zpool_dataset))
        self.mock_export.assert_called_once_with()
