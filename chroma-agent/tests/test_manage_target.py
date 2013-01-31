#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================
from chroma_agent.action_plugins.manage_targets import writeconf_target, format_target, _get_nvpairid_from_xml

from django.utils import unittest
import chroma_agent.shell


class CommandCaptureTestCase(unittest.TestCase):
    results = {}

    def setUp(self):
        self._command_history = []

        def fake_shell(args):
            self._command_history.append(args)
            if tuple(args) in self.results:
                return self.results[tuple(args)]

        self._old_shell = chroma_agent.shell.try_run
        chroma_agent.shell.try_run = fake_shell

    def assertRan(self, command):
        self.assertIn(command, self._command_history)

    def tearDown(self):
        chroma_agent.shell.try_run = self._old_shell


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
                         mgsnode = [['1.2.3.4@tcp', '4.3.2.1@tcp1'], ['1.2.3.5@tcp', '4.3.2.2@tcp1']])
        self.assertRan(["tunefs.lustre", "--erase-params", "--mgsnode=1.2.3.4@tcp,4.3.2.1@tcp1", "--mgsnode=1.2.3.5@tcp,4.3.2.2@tcp1", "--writeconf", "/dev/foo"])

    def test_unknown_opt(self):
        self.assertRaises(TypeError, writeconf_target, unknown='whatever')


class TestFormatTarget(CommandCaptureTestCase):
    results = {
        ("blkid", "-o", "value", "-s", "UUID", "/dev/foo"): "123456",
        ("dumpe2fs", "-h", "/dev/foo"): """
        Inode count: 1
        Inode size: 2
"""
    }

    def test_mdt_mkfs(self):
        format_target(device='/dev/foo',
                          target_types=['mdt'])
        self.assertRan(["mkfs.lustre", "--mdt", "/dev/foo"])

    def test_mgs_mkfs(self):
        format_target(device='/dev/foo',
                          target_types=['mgs'])
        self.assertRan(["mkfs.lustre", "--mgs", "/dev/foo"])

    def test_ost_mkfs(self):
        format_target(device='/dev/foo',
                          target_types=['ost'])
        self.assertRan(["mkfs.lustre", "--ost", "/dev/foo"])

    def test_single_mgs_one_nid(self):
        format_target(device='/dev/foo',
                      target_types=['ost'],
                      mgsnode = [['1.2.3.4@tcp']])
        self.assertRan(["mkfs.lustre", "--ost", "--mgsnode=1.2.3.4@tcp", "/dev/foo"])

    def test_mgs_pair_one_nid(self):
        format_target(device='/dev/foo',
                      target_types=['ost'],
                      mgsnode = [['1.2.3.4@tcp'], ['1.2.3.5@tcp']])
        self.assertRan(["mkfs.lustre", "--ost", "--mgsnode=1.2.3.4@tcp", "--mgsnode=1.2.3.5@tcp", "/dev/foo"])

    def test_single_mgs_multiple_nids(self):
        format_target(device='/dev/foo',
                      target_types=['ost'],
                      mgsnode = [['1.2.3.4@tcp', '4.3.2.1@tcp1']])
        self.assertRan(["mkfs.lustre", "--ost", "--mgsnode=1.2.3.4@tcp,4.3.2.1@tcp1", "/dev/foo"])

    def test_mgs_pair_multiple_nids(self):
        format_target(device='/dev/foo',
                      target_types=['ost'],
                      mgsnode = [['1.2.3.4@tcp', '4.3.2.1@tcp1'], ['1.2.3.5@tcp', '4.3.2.2@tcp1']])
        self.assertRan(["mkfs.lustre", "--ost", "--mgsnode=1.2.3.4@tcp,4.3.2.1@tcp1", "--mgsnode=1.2.3.5@tcp,4.3.2.2@tcp1", "/dev/foo"])

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        format_target(device='/dev/foo',
                          target_types=['mgs', 'mdt'])
        self.assertRan(["mkfs.lustre", "--mgs", "--mdt", "/dev/foo"])

    def test_dict_opts(self):
        format_target(device = "/dev/foo", param={'foo': 'bar', 'baz': 'qux thud'})
        self.assertRan(["mkfs.lustre", "--param", "foo=bar", "--param", "baz=qux thud", "/dev/foo"])

    def test_flag_opts(self):
        format_target(device = "/dev/foo", dryrun=True)
        self.assertRan(["mkfs.lustre", "--dryrun", "/dev/foo"])

    def test_zero_opt(self):
        format_target(device = "/dev/foo", index=0,
            mkfsoptions='-x 30 --y --z=83')
        self.assertRan(["mkfs.lustre", "--index=0", "--mkfsoptions=-x 30 --y --z=83", "/dev/foo"])

    def test_other_opts(self):
        format_target(device = "/dev/foo", index=42,
                          mkfsoptions='-x 30 --y --z=83')
        self.assertRan(["mkfs.lustre", "--index=42", "--mkfsoptions=-x 30 --y --z=83", "/dev/foo"])

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
