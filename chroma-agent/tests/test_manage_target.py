from chroma_agent.action_plugins.manage_targets import writeconf_target, format_target, _get_nvpairid_from_xml, check_block_device
from chroma_agent.chroma_common.blockdevices.blockdevice import BlockDevice

from tests.command_capture_testcase import CommandCaptureTestCase

from django.utils import unittest


class TestWriteconfTarget(CommandCaptureTestCase):
    def test_mdt_tunefs(self):
        writeconf_target(device='/dev/foo',
                            target_types=['mdt'])
        self.assertRan(['tunefs.lustre', '--mdt', '/dev/foo'])

    def test_mgs_tunefs(self):
        writeconf_target(device='/dev/foo',
                            target_types=['mgs'])
        self.assertRan(["tunefs.lustre", "--mgs", "/dev/foo"])

    def test_ost_tunefs(self):
        writeconf_target(device='/dev/foo',
                            target_types=['ost'])
        self.assertRan(["tunefs.lustre", "--ost", "/dev/foo"])

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        writeconf_target(device='/dev/foo',
                            target_types=['mgs', 'mdt'])
        self.assertRan(["tunefs.lustre", "--mgs", "--mdt", "/dev/foo"])

    def test_dict_opts(self):
        writeconf_target(device='/dev/foo',
            param={'foo': 'bar', 'baz': 'qux thud'})
        self.assertRan(["tunefs.lustre", "--param", "foo=bar", "--param", "baz=qux thud", "/dev/foo"])

    def test_flag_opts(self):
        writeconf_target(device='/dev/foo',
            dryrun=True)
        self.assertRan(["tunefs.lustre", "--dryrun", "/dev/foo"])

    def test_other_opts(self):
        writeconf_target(device='/dev/foo',
            index='42', mountfsoptions='-x 30 --y --z=83')
        self.assertRan(["tunefs.lustre", "--index=42", "--mountfsoptions=-x 30 --y --z=83", "/dev/foo"])

    def test_mgsnode_multiple_nids(self):
        writeconf_target(device='/dev/foo',
                         writeconf = True,
                         erase_params = True,
                         mgsnode = [['1.2.3.4@tcp', '4.3.2.1@tcp1'], ['1.2.3.5@tcp0', '4.3.2.2@tcp1']])
        self.assertRan(["tunefs.lustre", "--erase-params", "--mgsnode=1.2.3.4@tcp,4.3.2.1@tcp1", "--mgsnode=1.2.3.5@tcp0,4.3.2.2@tcp1", "--writeconf", "/dev/foo"])

    def test_unknown_opt(self):
        self.assertRaises(TypeError, writeconf_target, unknown='whatever')


class TestFormatTarget(CommandCaptureTestCase):
    results = {
        ("blkid", "-p", "-o", "value", "-s", "UUID", "/dev/foo"): "123456\n",
        ("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/foo"): "ext4\n",
        ("dumpe2fs", "-h", "/dev/foo"): "        Inode count: 1\n        Inode size: 2\n"}

    def test_mdt_mkfs(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      device_type = block_device.device_type,
                      target_name = "MDT0000",
                      backfstype = block_device.preferred_fstype,
                      target_types=['mdt'])
        self.assertRan(["mkfs.lustre",
                        "--mdt",
                        "--backfstype=%s" % block_device.preferred_fstype,
                        block_device.device_path])

    def test_mgs_mkfs(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      device_type = block_device.device_type,
                      target_name = "MGS0000",
                      backfstype = block_device.preferred_fstype,
                      target_types=['mgs'])
        self.assertRan(["mkfs.lustre",
                        "--mgs",
                        "--backfstype=%s" % block_device.preferred_fstype,
                        block_device.device_path])

    def test_ost_mkfs(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      device_type = block_device.device_type,
                      target_name = "MDT0000",
                      backfstype = block_device.preferred_fstype,
                      target_types=['ost'])
        self.assertRan(["mkfs.lustre",
                        "--ost",
                        "--backfstype=%s" % block_device.preferred_fstype,
                        block_device.device_path])

    def test_single_mgs_one_nid(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      device_type = block_device.device_type,
                      target_name = "OST0000",
                      backfstype = block_device.preferred_fstype,
                      target_types=['ost'],
                      mgsnode=[['1.2.3.4@tcp']])
        self.assertRan(["mkfs.lustre",
                        "--ost",
                        "--mgsnode=1.2.3.4@tcp",
                        "--backfstype=%s" % block_device.preferred_fstype,
                        block_device.device_path])

    def test_mgs_pair_one_nid(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      target_types=['ost'],
                      target_name = "OST0000",
                      backfstype = block_device.preferred_fstype,
                      device_type = block_device.device_type,
                      mgsnode=[['1.2.3.4@tcp'], ['1.2.3.5@tcp']])
        self.assertRan(["mkfs.lustre", "--ost",
                        "--mgsnode=1.2.3.4@tcp",
                        "--mgsnode=1.2.3.5@tcp",
                        "--backfstype=%s" % block_device.preferred_fstype,
                        block_device.device_path])

    def test_single_mgs_multiple_nids(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      target_types=['ost'],
                      target_name = "OST0000",
                      backfstype = block_device.preferred_fstype,
                      device_type = block_device.device_type,
                      mgsnode=[['1.2.3.4@tcp0', '4.3.2.1@tcp1']])
        self.assertRan(["mkfs.lustre",
                        "--ost",
                        "--mgsnode=1.2.3.4@tcp0,4.3.2.1@tcp1",
                        "--backfstype=%s" % block_device.preferred_fstype,
                        block_device.device_path])

    def test_mgs_pair_multiple_nids(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      target_name = "OST0000",
                      backfstype = block_device.preferred_fstype,
                      target_types =['ost'],
                      device_type = block_device.device_type,
                      mgsnode=[['1.2.3.4@tcp0', '4.3.2.1@tcp1'], ['1.2.3.5@tcp0', '4.3.2.2@tcp1']])
        self.assertRan(["mkfs.lustre",
                        "--ost",
                        "--mgsnode=1.2.3.4@tcp0,4.3.2.1@tcp1",
                        "--mgsnode=1.2.3.5@tcp0,4.3.2.2@tcp1",
                        "--backfstype=%s" % block_device.preferred_fstype,
                        block_device.device_path])

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      device_type = block_device.device_type,
                      target_name = "MGS0000",
                      backfstype = block_device.preferred_fstype,
                      target_types=['mgs', 'mdt'])
        self.assertRan(["mkfs.lustre",
                        "--mgs",
                        "--mdt", "--backfstype=%s" % block_device.preferred_fstype,
                        block_device.device_path])

    def test_dict_opts(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      device_type = block_device.device_type,
                      target_name = "MGS0000",
                      backfstype = block_device.preferred_fstype,
                      param={'foo': 'bar', 'baz': 'qux thud'})
        self.assertRan(["mkfs.lustre",
                        "--param",
                        "foo=bar",
                        "--param",
                        "baz=qux thud",
                        "--backfstype=%s" % block_device.preferred_fstype,
                       block_device.device_path])

    def test_flag_opts(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      device_type = block_device.device_type,
                      target_name = "MGS0000",
                      backfstype = block_device.preferred_fstype,
                      dryrun=True)
        self.assertRan(["mkfs.lustre",
                        "--dryrun",
                        "--backfstype=%s" % block_device.preferred_fstype,
                        block_device.device_path])

    def test_zero_opt(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      device_type = block_device.device_type,
                      target_name = "MGS0000",
                      backfstype = block_device.preferred_fstype,
                      index=0,
                      mkfsoptions='-x 30 --y --z=83')
        self.assertRan(["mkfs.lustre",
                        "--index=0",
                        "--mkfsoptions=-x 30 --y --z=83",
                        "--backfstype=%s" % block_device.preferred_fstype,
                       block_device.device_path])

    def test_other_opts(self):
        block_device = BlockDevice('linux', '/dev/foo')

        format_target(device = block_device.device_path,
                      device_type = block_device.device_type,
                      target_name = "MGS0000",
                      backfstype = block_device.preferred_fstype,
                      index=42,
                      mkfsoptions='-x 30 --y --z=83')
        self.assertRan(["mkfs.lustre",
                        "--index=42",
                        "--mkfsoptions=-x 30 --y --z=83",
                         "--backfstype=%s" % block_device.preferred_fstype,
                       block_device.device_path])

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
        self.results = {
            ("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/sdb"): (0, "ext4\n", "")
        }

        self.assertEqual(check_block_device("linux", "/dev/sdb"), 'ext4')

    def test_mbr_device(self):
        self.results = {
            ("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/sdb"): (0, "\n", "")
        }

        self.assertEqual(check_block_device("linux", "/dev/sdb"), None)

    def test_empty_device(self):
        self.results = {
            ("blkid", "-p", "-o", "value", "-s", "TYPE", "/dev/sdb"): (2, "", "")
        }

        self.assertEqual(check_block_device("linux", "/dev/sdb"), None)
