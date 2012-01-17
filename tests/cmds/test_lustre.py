
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from hydra_agent.cmds import lustre
from django.utils import unittest


class TestLustreTunefsCommand(unittest.TestCase):
    def test_mdt_tunefs(self):
        cmd = lustre.tunefs(device='/dev/foo',
                            target_types=['mdt'])
        self.assertEqual(cmd, "tunefs.lustre --mdt /dev/foo")

    def test_mgs_tunefs(self):
        cmd = lustre.tunefs(device='/dev/foo',
                            target_types=['mgs'])
        self.assertEqual(cmd, "tunefs.lustre --mgs /dev/foo")

    def test_ost_tunefs(self):
        cmd = lustre.tunefs(device='/dev/foo',
                            target_types=['ost'])
        self.assertEqual(cmd, "tunefs.lustre --ost /dev/foo")

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        cmd = lustre.tunefs(device='/dev/foo',
                            target_types=['mgs', 'mdt'])
        self.assertEqual(cmd, "tunefs.lustre --mgs --mdt /dev/foo")

    def test_dict_opts(self):
        cmd = lustre.tunefs(param={'foo': 'bar', 'baz': 'qux thud'})
        self.assertEqual(cmd, 'tunefs.lustre --param foo=bar --param baz="qux thud"')

    def test_flag_opts(self):
        cmd = lustre.tunefs(dryrun=True)
        self.assertEqual(cmd, "tunefs.lustre --dryrun")

    def test_other_opts(self):
        cmd = lustre.tunefs(index='42',
                            mountfsoptions='-x 30 --y --z=83')
        self.assertEqual(cmd, 'tunefs.lustre --index=42 --mountfsoptions="-x 30 --y --z=83"')

    def test_unknown_opt(self):
        self.assertRaises(TypeError, lustre.tunefs, unknown='whatever')


class TestLustreMkfsCommand(unittest.TestCase):
    def test_mdt_mkfs(self):
        cmd = lustre.mkfs(device='/dev/foo',
                          target_types=['mdt'])
        self.assertEqual(cmd, "mkfs.lustre --mdt /dev/foo")

    def test_mgs_mkfs(self):
        cmd = lustre.mkfs(device='/dev/foo',
                          target_types=['mgs'])
        self.assertEqual(cmd, "mkfs.lustre --mgs /dev/foo")

    def test_ost_mkfs(self):
        cmd = lustre.mkfs(device='/dev/foo',
                          target_types=['ost'])
        self.assertEqual(cmd, "mkfs.lustre --ost /dev/foo")

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        cmd = lustre.mkfs(device='/dev/foo',
                          target_types=['mgs', 'mdt'])
        self.assertEqual(cmd, "mkfs.lustre --mgs --mdt /dev/foo")

    def test_dict_opts(self):
        cmd = lustre.mkfs(param={'foo': 'bar', 'baz': 'qux thud'})
        self.assertEqual(cmd, 'mkfs.lustre --param foo=bar --param baz="qux thud"')

    def test_flag_opts(self):
        cmd = lustre.mkfs(dryrun=True)
        self.assertEqual(cmd, "mkfs.lustre --dryrun")

    def test_other_opts(self):
        cmd = lustre.mkfs(index='42',
                          mkfsoptions='-x 30 --y --z=83')
        self.assertEqual(cmd, 'mkfs.lustre --index=42 --mkfsoptions="-x 30 --y --z=83"')

    def test_unknown_opt(self):
        self.assertRaises(TypeError, lustre.mkfs, unknown='whatever')


class TestLustreMountCommands(unittest.TestCase):
    def test_target_mount(self):
        cmd = lustre.mount(device='/dev/null', dir='/mnt/lustre/target')
        self.assertEqual(cmd, "mount -t lustre /dev/null /mnt/lustre/target")

    def test_target_unmount(self):
        cmd = lustre.umount(dir='/mnt/lustre/target')
        self.assertEqual(cmd, "umount /mnt/lustre/target")

    def test_client_mount(self):
        cmd = lustre.mount(device='mgs:/testfs',
                           dir='/mnt/lustre')
        self.assertEqual(cmd, "mount -t lustre mgs:/testfs /mnt/lustre")

    def test_missing_args(self):
        self.assertRaises(ValueError, lustre.mount, device='/foo/bar')

    def test_both_umount(self):
        cmd = lustre.umount(device='/dev/null',
                            dir='/mnt/lustre/target')
        self.assertEqual(cmd, "umount /dev/null || umount /mnt/lustre/target")

    def test_all_unmount(self):
        cmd = lustre.umount()
        self.assertEqual(cmd, "umount -a -tlustre")


class TestLustreLNetCommands(unittest.TestCase):
    def test_lnet_load(self):
        self.assertEqual(lustre.lnet_load(), "modprobe lnet")

    def test_lnet_unload(self):
        self.assertEqual(lustre.lnet_unload(), "lustre_rmmod")

    def test_lnet_start(self):
        self.assertEqual(lustre.lnet_start(), "lctl net up")

    def test_lnet_stop(self):
        self.assertEqual(lustre.lnet_stop(), "lctl net down || (lustre_rmmod; lctl net down)")

if __name__ == "__main__":
    unittest.main()
