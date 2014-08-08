from chroma_agent.chroma_common.blockdevices.blockdevice_zfs import BlockDeviceZfs
from tests.command_capture_testcase import CommandCaptureTestCase


class TestBlockDeviceZFS(CommandCaptureTestCase):
    def setUp(self):
        super(TestBlockDeviceZFS, self).setUp()

        self.blockdevice = BlockDeviceZfs('zfs', 'zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333/ost_index0')

    def test_filesystem_type(self):
        self.assertEqual('zfs', self.blockdevice.filesystem_type)

    def test_uuid(self):
        self.results = {
            ("zfs", "list", "-o", "name,guid"): (0, """NAME                                                                  GUID\n
zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333             1672148304068375665\n
zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333/ost_index0  169883839435093209\n
zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP5555555             16305972746322234197\n
zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP5555555/ost_index2  5057404647579993229\n""", 0)}

        self.assertEqual('169883839435093209', self.blockdevice.uuid)

    def test_preferred_fstype(self):
        self.assertEqual('zfs', self.blockdevice.preferred_fstype)

    def test_zdb_values(self):
        self.results = {
            ("zdb", "-h", "zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333/ost_index0"):
                "Dataset zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333/ost_index0 [ZPL], ID 40, cr_txg 20, 2.38M, 283 objects\n",
            ("zdb", "-h", "zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333"):
                """\n
History:\n
2014-09-24.08:54:10 zpool create -f zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333 /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_WD-WMAP3333333\n
2014-09-24.08:54:10 [internal pool create txg:5] pool spa 5000; zfs spa 5000; zpl 5; uts lotus-19vm6 2.6.32-431.20.5.el6_lustre.x86_64 #1 SMP Fri Jul 25 16:51:42 PDT 2014 x86_64\n

2014-09-24.08:55:22 [internal create txg:20] dataset = 40\n
2014-09-24.08:55:22 [internal property set txg:21] canmount=0 dataset = 40\n
2014-09-24.08:55:22 [internal property set txg:21] xattr=2 dataset = 40\n
2014-09-24.08:55:22 zfs create -o canmount=off -o xattr=sa zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333/ost_index0\n
2014-09-24.08:55:22 [internal property set txg:22] lustre:version=1 dataset = 40\n
2014-09-24.08:55:22 [internal property set txg:23] lustre:flags=98 dataset = 40\n
2014-09-24.08:55:22 [internal property set txg:24] lustre:index=0 dataset = 40\n
2014-09-24.08:55:22 [internal property set txg:25] lustre:fsname=efs dataset = 40\n
2014-09-24.08:55:22 [internal property set txg:26] lustre:svname=efs:OST0000 dataset = 40\n
2014-09-24.08:55:22 [internal property set txg:27] lustre:mgsnode=10.14.82.251@tcp dataset = 40\n
2014-09-24.08:55:23 [internal property set txg:28] lustre:version=1 dataset = 40\n
2014-09-24.08:55:23 [internal property set txg:29] lustre:flags=34 dataset = 40\n
2014-09-24.08:55:23 [internal property set txg:30] lustre:index=0 dataset = 40\n
2014-09-24.08:55:23 [internal property set txg:31] lustre:fsname=efs dataset = 40\n
2014-09-24.08:55:23 [internal property set txg:32] lustre:svname=efs:OST0000 dataset = 40\n
2014-09-24.08:55:23 [internal property set txg:33] lustre:mgsnode=10.14.82.251@tcp dataset = 40\n
2014-09-24.08:55:24 [internal property set txg:36] lustre:svname=efs-OST0000 dataset = 40\n
2014-09-24.08:55:24 [internal property set txg:36] lustre:svname=shoud-be-ignored dataset = 20\n"""}

        zdb_values = self.blockdevice.zdb_values

        self.assertEqual(zdb_values['fsname'], 'efs')
        self.assertEqual(zdb_values['svname'], 'efs-OST0000')
        self.assertEqual(zdb_values['flags'], '34')

    def mgs_targets(self, log):
        zdb_values = self.zdb_values

        if ('fsname' in zdb_values) and ('svname' in zdb_values):
            return {zdb_values['fsname']: {"name": zdb_values['svname'][len(zdb_values['fsname']) + 1:]}}
        else:
            return {}

    def targets(self, uuid_name_to_target, device, log):
        log.info("Searching device %s of type %s, uuid %s for a Lustre filesystem" % (device['path'], device['type'], device['uuid']))

        zdb_values = self.zdb_values

        if ('svname' not in zdb_values) or ('flags' not in zdb_values):
            log.info("Device %s did not have a Lustre zdb values required" % device['path'])
            return self.TargetsInfo([], None)

        # For a Lustre block device, extract name and params
        # ==================================================
        name = zdb_values['svname']
        flags = int(zdb_values['flags'], 16)

        if  ('mgsnode' in zdb_values):
            params = {'mgsnode': [zdb_values['mgsnode']]}
        else:
            params = {}

        if name.find("ffff") != -1:
            log.info("Device %s reported an unregistered lustre target and so will not be reported" % device['path'])
            return self.TargetsInfo([], None)

        if flags & 0x0005 == 0x0005:
            # For combined MGS/MDT volumes, synthesise an 'MGS'
            names = ["MGS", name]
        else:
            names = [name]

        return self.TargetsInfo(names, params)
