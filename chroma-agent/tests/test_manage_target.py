#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================
from chroma_agent.action_plugins.manage_targets import writeconf_target, format_target

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

    def test_other_opts(self):
        format_target(device = "/dev/foo", index='42',
                          mkfsoptions='-x 30 --y --z=83')
        self.assertRan(["mkfs.lustre", "--index=42", "--mkfsoptions=-x 30 --y --z=83", "/dev/foo"])

    def test_unknown_opt(self):
        self.assertRaises(TypeError, format_target, unknown='whatever')
