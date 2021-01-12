""" Data for use in emf_common unit tests, mostly example commandline stdout """

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
