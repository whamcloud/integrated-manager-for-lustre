from hydra_agent.cmds import lustre
import unittest

class TestLustreTunefsCommand(unittest.TestCase):
    def test_mdt_tunefs(self):
        cmd = lustre.tunefs(device='/dev/foo',
                            target_types=['mdt'])
        assert cmd == "tunefs.lustre --mdt /dev/foo"

    def test_mgs_tunefs(self):
        cmd = lustre.tunefs(device='/dev/foo',
                            target_types=['mgs'])
        assert cmd == "tunefs.lustre --mgs /dev/foo"

    def test_ost_tunefs(self):
        cmd = lustre.tunefs(device='/dev/foo',
                            target_types=['ost'])
        assert cmd == "tunefs.lustre --ost /dev/foo"

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        cmd = lustre.tunefs(device='/dev/foo',
                            target_types=['mgs', 'mdt'])
        assert cmd == "tunefs.lustre --mgs --mdt /dev/foo"

    def test_dict_opts(self):
        cmd = lustre.tunefs(param={'foo': 'bar', 'baz': 'qux thud'})
        assert cmd == 'tunefs.lustre --param foo=bar --param baz="qux thud"'

    def test_flag_opts(self):
        cmd = lustre.tunefs(dryrun=True)
        assert cmd == "tunefs.lustre --dryrun"

    def test_other_opts(self):
        cmd = lustre.tunefs(index='42',
                            mountfsoptions='-x 30 --y --z=83')
        assert cmd == 'tunefs.lustre --index=42 --mountfsoptions="-x 30 --y --z=83"'

    def test_unknown_opt(self):
        try:
            cmd = lustre.tunefs(unknown='whatever')
        except TypeError:
            pass
        else:
            fail("Expected TypeError")

class TestLustreMkfsCommand(unittest.TestCase):
    def test_mdt_mkfs(self):
        cmd = lustre.mkfs(device='/dev/foo',
                          target_types=['mdt'])
        assert cmd == "mkfs.lustre --mdt /dev/foo"

    def test_mgs_mkfs(self):
        cmd = lustre.mkfs(device='/dev/foo',
                          target_types=['mgs'])
        assert cmd == "mkfs.lustre --mgs /dev/foo"

    def test_ost_mkfs(self):
        cmd = lustre.mkfs(device='/dev/foo',
                          target_types=['ost'])
        assert cmd == "mkfs.lustre --ost /dev/foo"

    # this test does double-duty in testing tuple opts and also
    # the multiple target_types special case
    def test_tuple_opts(self):
        cmd = lustre.mkfs(device='/dev/foo',
                          target_types=['mgs', 'mdt'])
        assert cmd == "mkfs.lustre --mgs --mdt /dev/foo"

    def test_dict_opts(self):
        cmd = lustre.mkfs(param={'foo': 'bar', 'baz': 'qux thud'})
        assert cmd == 'mkfs.lustre --param foo=bar --param baz="qux thud"'

    def test_flag_opts(self):
        cmd = lustre.mkfs(dryrun=True)
        assert cmd == "mkfs.lustre --dryrun"

    def test_other_opts(self):
        cmd = lustre.mkfs(index='42',
                          mkfsoptions='-x 30 --y --z=83')
        assert cmd == 'mkfs.lustre --index=42 --mkfsoptions="-x 30 --y --z=83"'

    def test_unknown_opt(self):
        try:
            cmd = lustre.mkfs(unknown='whatever')
        except TypeError:
            pass
        else:
            fail("Expected TypeError")

class TestLustreMountCommands(unittest.TestCase):
    def test_target_mount(self):
        cmd = lustre.mount(device='/dev/null', dir='/mnt/lustre/target')
        assert cmd == "mount -t lustre /dev/null /mnt/lustre/target"

    def test_target_unmount(self):
        cmd = lustre.umount(dir='/mnt/lustre/target')
        assert cmd == "umount /mnt/lustre/target"

    def test_client_mount(self):
        cmd = lustre.mount(device='mgs:/testfs',
                           dir='/mnt/lustre')
        assert cmd == "mount -t lustre mgs:/testfs /mnt/lustre"

    def test_missing_args(self):
        try:
            cmd = lustre.mount(device='/foo/bar')
        except ValueError:
            pass
        else:
            fail("Expected ValueError")

    def test_both_umount(self):
        cmd = lustre.umount(device='/dev/null',
                            dir='/mnt/lustre/target')
        assert cmd == "umount /dev/null || umount /mnt/lustre/target"

    def test_all_unmount(self):
        cmd = lustre.umount()
        assert cmd == "umount -a -tlustre"

class TestLustreLNetCommands(unittest.TestCase):
    def test_lnet_load(self):
        assert lustre.lnet_load() == "modprobe lnet"

    def test_lnet_unload(self):
        assert lustre.lnet_unload() == "lustre_rmmod || lctl net down && lustre_rmmod"

    def test_lnet_start(self):
        assert lustre.lnet_start() == "lctl net up"

    def test_lnet_stop(self):
        assert lustre.lnet_stop() == "lctl net down || (lustre_rmmod; lctl net down)"

if __name__ == "__main__":
    unittest.main()
