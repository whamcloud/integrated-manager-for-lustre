from chroma_agent.action_plugins.manage_targets import writeconf_target, format_target, _get_nvpairid_from_xml, check_block_device
from chroma_agent.chroma_common.blockdevices.blockdevice import BlockDevice

from tests.command_capture_testcase import CommandCaptureTestCase, CommandCaptureCommand

from django.utils import unittest


class TestWriteconfTarget(CommandCaptureTestCase):
    def test_mdt_tunefs(self):
        self.add_command(('tunefs.lustre', '--mdt', '/dev/foo'))

        writeconf_target(device='/dev/foo',
                            target_types=['mdt'])
        self.assertRanAllCommands()

    def test_mgs_tunefs(self):
        self.add_command(("tunefs.lustre", "--mgs", "/dev/foo"))

        writeconf_target(device='/dev/foo',
                            target_types=['mgs'])
        self.assertRanAllCommands()

    def test_ost_tunefs(self):
        self.add_command(("tunefs.lustre", "--ost", "/dev/foo"))

        writeconf_target(device='/dev/foo',
                            target_types=['ost'])
        self.assertRanAllCommands()

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        self.add_command(("tunefs.lustre", "--mgs", "--mdt", "/dev/foo"))

        writeconf_target(device='/dev/foo',
                            target_types=['mgs', 'mdt'])
        self.assertRanAllCommands()

    def test_dict_opts(self):
        self.add_command(("tunefs.lustre", "--param", "foo=bar", "--param", "baz=qux thud", "/dev/foo"))

        writeconf_target(device='/dev/foo',
            param={'foo': 'bar', 'baz': 'qux thud'})
        self.assertRanAllCommands()

    def test_flag_opts(self):
        self.add_command(("tunefs.lustre", "--dryrun", "/dev/foo"))

        writeconf_target(device='/dev/foo',
            dryrun=True)
        self.assertRanAllCommands()

    def test_other_opts(self):
        self.add_command(("tunefs.lustre", "--index=42", "--mountfsoptions=-x 30 --y --z=83", "/dev/foo"))

        writeconf_target(device='/dev/foo',
            index='42', mountfsoptions='-x 30 --y --z=83')
        self.assertRanAllCommands()

    def test_mgsnode_multiple_nids(self):
        self.add_command(("tunefs.lustre", "--erase-params", "--mgsnode=1.2.3.4@tcp,4.3.2.1@tcp1", "--mgsnode=1.2.3.5@tcp0,4.3.2.2@tcp1", "--writeconf", "/dev/foo"))

        writeconf_target(device='/dev/foo',
                         writeconf = True,
                         erase_params = True,
                         mgsnode = [['1.2.3.4@tcp', '4.3.2.1@tcp1'], ['1.2.3.5@tcp0', '4.3.2.2@tcp1']])
        self.assertRanAllCommands()

    def test_unknown_opt(self):
        self.assertRaises(TypeError, writeconf_target, unknown='whatever')


class TestFormatTarget(CommandCaptureTestCase):
    block_device_list = [BlockDevice('linux', '/dev/foo'),
                         BlockDevice('zfs', 'lustre1')]

    def _mkfs_path(self, block_device, target_name):
        if (block_device.device_type == 'linux'):
            return block_device.device_path
        elif (block_device.device_type == 'zfs'):
            return "%s/%s" % (block_device.device_path, target_name)

        assert "Unknown device type %s" % block_device.device_type

    def _setup_run_exceptions(self, block_device, run_args):
        self._run_command = CommandCaptureCommand(run_args)

        self.add_commands(CommandCaptureCommand(("dumpe2fs", "-h", "/dev/foo"), stdout="Inode size: 1024\nInode count: 1024\n"),
                          CommandCaptureCommand(("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/foo"), stdout="%s\n" % block_device.preferred_fstype),
                          CommandCaptureCommand(("blkid", "-p", "-o", "value", "-s", "UUID", "/dev/foo"), stdout="123456789\n"),
                          CommandCaptureCommand(("zfs", "get", "-H", "-o", "value", "guid", "lustre1"), stdout="9845118046416187754"),
                          CommandCaptureCommand(("modprobe", "osd_%s" % block_device.preferred_fstype)),
                          self._run_command)

    def test_mdt_mkfs(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--mdt",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        self._mkfs_path(block_device, "MDT0000")))

            format_target(device = block_device.device_path,
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
                                        self._mkfs_path(block_device, "MGS0000")))

            format_target(device = block_device.device_path,
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
                                        self._mkfs_path(block_device, "MDT0000")))

            format_target(device = block_device.device_path,
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
                                        self._mkfs_path(block_device, "OST0000")))

            format_target(device = block_device.device_path,
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
                                        self._mkfs_path(block_device, "OST0000")))

            format_target(device = block_device.device_path,
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
                                        self._mkfs_path(block_device, "OST0000")))

            format_target(device = block_device.device_path,
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
                                        self._mkfs_path(block_device, "OST0000")))

            format_target(device = block_device.device_path,
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
                                        self._mkfs_path(block_device, "MGS0000")))

            format_target(device = block_device.device_path,
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
                                        self._mkfs_path(block_device, "MGS0000")))

            format_target(device = block_device.device_path,
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
                                        self._mkfs_path(block_device, "MGS0000")))

            format_target(device = block_device.device_path,
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
                                        "--mkfsoptions=-x 30 --y --z=83",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        self._mkfs_path(block_device, "MGS0000")))

            format_target(device = block_device.device_path,
                          device_type = block_device.device_type,
                          target_name = "MGS0000",
                          backfstype = block_device.preferred_fstype,
                          index=0,
                          mkfsoptions='-x 30 --y --z=83')
            self.assertRanCommand(self._run_command)

    def test_other_opts(self):
        for block_device in self.block_device_list:
            self._setup_run_exceptions(block_device,
                                       ("mkfs.lustre",
                                        "--index=42",
                                        "--mkfsoptions=-x 30 --y --z=83",
                                        "--backfstype=%s" % block_device.preferred_fstype,
                                        self._mkfs_path(block_device, "MGS0000")))

            format_target(device = block_device.device_path,
                          device_type = block_device.device_type,
                          target_name = "MGS0000",
                          backfstype = block_device.preferred_fstype,
                          index=42,
                          mkfsoptions='-x 30 --y --z=83')

            self.assertRanCommand(self._run_command)

    def test_unknown_opt(self):
        self.assertRaises(TypeError, format_target, unknown='whatever')


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
        self.assertEqual('c2890397-e0a2-4759-8f4e-df5ed64e1518', _get_nvpairid_from_xml(self.xml_example))


class TestCheckBlockDevice(CommandCaptureTestCase):
    def test_occupied_device(self):
        self.add_commands(CommandCaptureCommand(("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/sdb"), stdout="ext4\n"))

        self.assertEqual(check_block_device("linux", "/dev/sdb"), 'ext4')

    def test_mbr_device(self):
        self.add_commands(CommandCaptureCommand(("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/sdb"), stdout="\n"))

        self.assertEqual(check_block_device("linux", "/dev/sdb"), None)

    def test_empty_device(self):
        self.add_commands(CommandCaptureCommand(("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/sdb"), rc=2))

        self.assertEqual(check_block_device("linux", "/dev/sdb"), None)
