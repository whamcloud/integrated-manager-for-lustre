# example outputs of ZFS userspace tools

single_online_pool = """   pool: mdt
     id: 1282621454842134742
  state: ONLINE
 status: The pool was last accessed by another system.
 action: The pool can be imported using its name or numeric identifier and
        the '-f' flag.
   see: http://zfsonlinux.org/msg/ZFS-8000-EY
 config:

        mdt                         ONLINE
          mirror-0                  ONLINE
            scsi-35000cca04b11cd50  ONLINE
            scsi-35000cca04b2deda0  ONLINE
          mirror-1                  ONLINE
            scsi-35000cca04b2ded10  ONLINE
            scsi-35000cca04b2b90b8  ONLINE
"""

single_longname_online_pool = """   pool: zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333
     id: 14342381916379020923
  state: ONLINE
 status: The pool was last accessed by another system.
 action: The pool can be imported using its name or numeric identifier and
        the '-f' flag.
   see: http://zfsonlinux.org/msg/ZFS-8000-EY
 config:

 zfs_pool_devdiskbyidscsi0QEMU_QEMU_HARDDISK_WDWMAP3333333       ONLINE
          sda       ONLINE
"""

single_dave_pool = """   pool: Dave
     id: 14342381916379020923
  state: ONLINE
 status: The pool was last accessed by another system.
 action: The pool can be imported using its name or numeric identifier and
        the '-f' flag.
   see: http://zfsonlinux.org/msg/ZFS-8000-EY
 config:

        Dave       ONLINE
          sda       ONLINE
"""

multiple_online_pools = """   pool: pool1
     id: 14342381916379020923
  state: ONLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

        pool1       ONLINE
          sda       ONLINE

   pool: pool1
     id: 11390096414938798867
  state: ONLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

        pool1       ONLINE
          sde       ONLINE
        cache
          sdd
"""

multiple_exported_online_offline_pools = """pool: zfsPool1
     id: 2234567890ABCDE
  state: ONLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

    zfsPool1  ONLINE
      sda  ONLINE

      pool: zfsPool2
     id: 111111111111111
  state: OFFLINE
 action: The pool will fail when it is imported. Because of the error below.
 config:

    zfsPool2  OFFLINE
      sdb  ONLINE

      pool: zfsPool3
     id: 222222222222222
  state: ONLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

    zfsPool3  ONLINE
      sdc  ONLINE
"""

multiple_exported_online_pools = """pool: zfsPool1
     id: 1234567890ABCDE
  state: ONLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

    zfsPool1  ONLINE
      sda  ONLINE

      pool: zfsPool2
     id: 111111111111111
  state: ONLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

    zfsPool2  ONLINE
      sdb  ONLINE

      pool: zfsPool3
     id: 222222222222222
  state: ONLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

    zfsPool3  ONLINE
      sdc  ONLINE
"""

single_raidz2_log_pool = """   pool: pool2
     id: 17952907889216060772
  state: ONLINE
 action: The pool can be imported using its name or numeric identifier.
 config:

        pool2       ONLINE
          raidz2-0  ONLINE
            sda     ONLINE
            sdc     ONLINE
            sdb     ONLINE
            sde     ONLINE
        logs
          sdd       ONLINE
"""

single_raidz2_scrub_pool = """  pool: zost09
 state: ONLINE
  scan: scrub repaired 0 in 0h0m with 0 errors on Tue Apr 11 18:07:44 2017
config:

        NAME           STATE     READ WRITE CKSUM
        zost09         ONLINE       0     0     0
          raidz2-0     ONLINE       0     0     0
            S3P1E0129  ONLINE       0     0     0
            S3P1E0130  ONLINE       0     0     0
            S3P1E0131  ONLINE       0     0     0
            S3P1E0132  ONLINE       0     0     0
            S3P1E0133  ONLINE       0     0     0
            S4P1E0128  ONLINE       0     0     0
            S4P1E0129  ONLINE       0     0     0
            S4P1E0130  ONLINE       0     0     0
            S4P1E0131  ONLINE       0     0     0
            S4P1E0132  ONLINE       0     0     0
            S4P1E0133  ONLINE       0     0     0

errors: No known data errors
"""

single_raidz2_unavail_pool = """   pool: zost04
     id: 14729155358256179095
  state: UNAVAIL
 status: The pool was last accessed by another system.
 action: The pool cannot be imported due to damaged devices or data.
   see: http://zfsonlinux.org/msg/ZFS-8000-EY
 config:

        zost04         UNAVAIL  insufficient replicas
          raidz2-0     UNAVAIL  insufficient replicas
            S2P1E0101  UNAVAIL
            S2P1E0102  UNAVAIL
            S2P1E0103  UNAVAIL
            S2P1E0104  UNAVAIL
            S2P1E0105  UNAVAIL
            S2P1E0106  UNAVAIL
            S4P1E0101  ONLINE
            S4P1E0102  ONLINE
            S4P1E0103  ONLINE
            mpathc     ONLINE
            S4P1E0105  ONLINE
"""

single_raidz2_unavail_pool_B = """   pool: zost04
     id: 222222222222222
  state: UNAVAIL
 status: The pool was last accessed by another system.
 action: The pool cannot be imported due to damaged devices or data.
   see: http://zfsonlinux.org/msg/ZFS-8000-EY
 config:

        zost04         UNAVAIL  insufficient replicas
          raidz2-0     UNAVAIL  insufficient replicas
            S2P1E0101  UNAVAIL
            S2P1E0102  UNAVAIL
            S2P1E0103  UNAVAIL
            S2P1E0104  UNAVAIL
            S2P1E0105  UNAVAIL
            S2P1E0106  UNAVAIL
            S4P1E0101  ONLINE
            S4P1E0102  ONLINE
            S4P1E0103  ONLINE
            mpathc     ONLINE
            S4P1E0105  ONLINE
"""

multiple_imported_pools_status = """  pool: zfsPool3
 state: ONLINE
  scan: scrub repaired 0 in 0h0m with 0 errors on Tue Apr 11 18:07:44 2017
config:

        NAME        STATE     READ WRITE CKSUM
        zfsPool3    ONLINE       0     0     0
          sda       ONLINE       0     0     0

errors: No known data errors

  pool: zfsPool1
 state: OFFLINE
  scan: none requested
config:

        NAME        STATE     READ WRITE CKSUM
        zfsPool1    OFFLINE       0     0     0
          sdd       OFFLINE       0     0     0

errors: No known data errors
"""
