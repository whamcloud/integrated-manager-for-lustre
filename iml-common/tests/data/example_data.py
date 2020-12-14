""" Data for use in iml_common unit tests, mostly example commandline stdout """

# example commandline stdout from command of the format:
# >> zfs get -Hp -o property,value all <zfs dataset path e.g. pool1/MGS>
zfs_example_properties = """type	filesystem
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
lustre:flags	37"""

# example commandline stdout from command of the format:
# >> dumpe2fs -h <ldiskfs device path e.g. /dev/sda1>
dumpe2fs_example_output = """
Filesystem volume name:   <none>
Last mounted on:          /boot
Filesystem UUID:          e77433f9-d9fb-48e7-b444-41a3c84016db
Filesystem magic number:  0xEF53
Filesystem revision #:    1 (dynamic)
Filesystem features:      has_journal ext_attr resize_inode dir_index filetype needs_recovery sparse_super
Filesystem flags:         signed_directory_hash
Default mount options:    user_xattr acl
Filesystem state:         clean
Errors behavior:          Continue
Filesystem OS type:       Linux
Inode count:              128016
Block count:              512000
Reserved block count:     25600
Free blocks:              308769
Free inodes:              127670
First block:              1
Block size:               1024
Fragment size:            1024
Reserved GDT blocks:      256
Blocks per group:         8192
Fragments per group:      8192
Inodes per group:         2032
Inode blocks per group:   254
Filesystem created:       Thu May 26 11:23:07 2016
Last mount time:          Thu Jun 30 06:21:32 2016
Last write time:          Thu Jun 30 06:21:32 2016
Mount count:              36
Maximum mount count:      -1
Last checked:             Thu May 26 11:23:07 2016
Check interval:           0 (<none>)
Lifetime writes:          1425 MB
Reserved blocks uid:      0 (user root)
Reserved blocks gid:      0 (group root)
First inode:              11
Inode size:               128
Journal inode:            8
Default directory hash:   half_md4
Directory Hash Seed:      0d04e737-aece-4ef7-9e21-1edea14ebcde
Journal backup:           inode blocks
Journal features:         journal_incompat_revoke
Journal size:             8M
Journal length:           8192
Journal sequence:         0x00000365
Journal start:            1"""

# example commandline stdout from command of the format:
# >> zpool get -Hp all <zpool name>
zpool_example_properties = """bob     size    10670309376     -
bob     capacity        0       -
bob     altroot -       default
bob     health  ONLINE  -
bob     guid    14447627934634597108    -
bob     version -       default
bob     bootfs  -       default
bob     delegation      on      default
bob     autoreplace     off     default
bob     cachefile       -       default
bob     failmode        panic   local
bob     listsnapshots   off     default
bob     autoexpand      off     default
bob     dedupditto      0       default
bob     dedupratio      1.00    -
bob     free    10670149632     -
bob     allocated       159744  -
bob     readonly        off     -
bob     ashift  0       default
bob     comment -       default
bob     expandsize      -       -
bob     freeing 0       -
bob     fragmentation   0       -
bob     leaked  0       -
bob     multihost       on      local
bob     feature@async_destroy   enabled local
bob     feature@empty_bpobj     active  local
bob     feature@lz4_compress    active  local
bob     feature@multi_vdev_crash_dump   enabled local
bob     feature@spacemap_histogram      active  local
bob     feature@enabled_txg     active  local
bob     feature@hole_birth      active  local
bob     feature@extensible_dataset      active  local
bob     feature@embedded_data   active  local
bob     feature@bookmarks       enabled local
bob     feature@filesystem_limits       enabled local
bob     feature@large_blocks    enabled local
bob     feature@large_dnode     enabled local
bob     feature@sha512  enabled local
bob     feature@skein   enabled local
bob     feature@edonr   enabled local
bob     feature@userobj_accounting      active  local"""
