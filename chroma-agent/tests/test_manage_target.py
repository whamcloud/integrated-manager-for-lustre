#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from chroma_agent.action_plugins.manage_targets import tunefs, mkfs
from django.utils import unittest


class TestLustreTunefsCommand(unittest.TestCase):
    def test_mdt_tunefs(self):
        cmd = tunefs(device='/dev/foo',
                            target_types=['mdt'])
        self.assertEqual(cmd, "tunefs.lustre --mdt /dev/foo")

    def test_mgs_tunefs(self):
        cmd = tunefs(device='/dev/foo',
                            target_types=['mgs'])
        self.assertEqual(cmd, "tunefs.lustre --mgs /dev/foo")

    def test_ost_tunefs(self):
        cmd = tunefs(device='/dev/foo',
                            target_types=['ost'])
        self.assertEqual(cmd, "tunefs.lustre --ost /dev/foo")

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        cmd = tunefs(device='/dev/foo',
                            target_types=['mgs', 'mdt'])
        self.assertEqual(cmd, "tunefs.lustre --mgs --mdt /dev/foo")

    def test_dict_opts(self):
        cmd = tunefs(param={'foo': 'bar', 'baz': 'qux thud'})
        self.assertEqual(cmd, 'tunefs.lustre --param foo=bar --param baz="qux thud"')

    def test_flag_opts(self):
        cmd = tunefs(dryrun=True)
        self.assertEqual(cmd, "tunefs.lustre --dryrun")

    def test_other_opts(self):
        cmd = tunefs(index='42',
                            mountfsoptions='-x 30 --y --z=83')
        self.assertEqual(cmd, 'tunefs.lustre --index=42 --mountfsoptions="-x 30 --y --z=83"')

    def test_unknown_opt(self):
        self.assertRaises(TypeError, tunefs, unknown='whatever')


class TestLustreMkfsCommand(unittest.TestCase):
    def test_mdt_mkfs(self):
        cmd = mkfs(device='/dev/foo',
                          target_types=['mdt'])
        self.assertEqual(cmd, "mkfs.lustre --mdt /dev/foo")

    def test_mgs_mkfs(self):
        cmd = mkfs(device='/dev/foo',
                          target_types=['mgs'])
        self.assertEqual(cmd, "mkfs.lustre --mgs /dev/foo")

    def test_ost_mkfs(self):
        cmd = mkfs(device='/dev/foo',
                          target_types=['ost'])
        self.assertEqual(cmd, "mkfs.lustre --ost /dev/foo")

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        cmd = mkfs(device='/dev/foo',
                          target_types=['mgs', 'mdt'])
        self.assertEqual(cmd, "mkfs.lustre --mgs --mdt /dev/foo")

    def test_dict_opts(self):
        cmd = mkfs(param={'foo': 'bar', 'baz': 'qux thud'})
        self.assertEqual(cmd, 'mkfs.lustre --param foo=bar --param baz="qux thud"')

    def test_flag_opts(self):
        cmd = mkfs(dryrun=True)
        self.assertEqual(cmd, "mkfs.lustre --dryrun")

    def test_other_opts(self):
        cmd = mkfs(index='42',
                          mkfsoptions='-x 30 --y --z=83')
        self.assertEqual(cmd, 'mkfs.lustre --index=42 --mkfsoptions="-x 30 --y --z=83"')

    def test_unknown_opt(self):
        self.assertRaises(TypeError, mkfs, unknown='whatever')
