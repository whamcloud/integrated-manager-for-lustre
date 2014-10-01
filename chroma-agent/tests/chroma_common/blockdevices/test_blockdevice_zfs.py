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
            ('zfs', 'get', '-H', '-o', 'value', 'guid', 'zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333/ost_index0'): (0, '169883839435093209\n', 0),
            ('zfs', 'list', '-o', 'name,guid'): (0, """NAME                                                                  GUID\n
zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333             1672148304068375665\n
zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333/ost_index0  169883839435093209\n
zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP5555555             16305972746322234197\n
zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP5555555/ost_index2  5057404647579993229\n""", 0)}

        self.assertEqual('169883839435093209', self.blockdevice.uuid)
        self.assertEqual('169883839435093209', self.blockdevice.uuid_new_method)

    def test_preferred_fstype(self):
        self.assertEqual('zfs', self.blockdevice.preferred_fstype)

    def test_property_values(self):
        self.results = {
            ("zfs", "get", "-Hp", "-o", "property,value", "all", "zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333/ost_index0"):
                """type	filesystem
garbageline followed by blank line

creation	1412156944
used	4602880
available	21002432000
referenced	4602880
compressratio	1.00x
mounted	no
quota	0
reservation	0
recordsize	131072
mountpoint	/zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP2222222/mgt
sharenfs	off
checksum	on
compression	off
atime	on
devices	on
exec	on
setuid	on
readonly	off
zoned	off
snapdir	hidden
aclinherit	restricted
canmount	off
xattr	sa
copies	1
version	5
utf8only	off
normalization	none
casesensitivity	sensitive
vscan	off
nbmand	off
sharesmb	off
refquota	0
refreservation	0
primarycache	all
secondarycache	all
usedbysnapshots	0
usedbydataset	4602880
usedbychildren	0
usedbyrefreservation	0
logbias	latency
dedup	off
mlslabel	none
sync	standard
refcompressratio	1.00x
written	4602880
logicalused	3874304
logicalreferenced	3874304
snapdev	hidden
acltype	off
context	none
fscontext	none
defcontext	none
rootcontext	none
relatime	off
lustre:version	1
lustre:fsname	efs
lustre:index	0
lustre:svname	efs-MDT0000
lustre:flags	37"""}

        zfs_properties = self.blockdevice.zfs_properties()

        self.assertEqual(zfs_properties['lustre:fsname'], 'efs')
        self.assertEqual(zfs_properties['lustre:svname'], 'efs-MDT0000')
        self.assertEqual(zfs_properties['lustre:flags'], '37')
