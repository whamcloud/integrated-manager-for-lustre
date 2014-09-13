include ../include/Makefile.lustre_build_meta

ZFS_RELEASE           := 0.6.2-1

CHROMA_EXTERNALS_SUBDIR := zfs

SRC_REPO               = $(JENKINS_ROOT_URL)/job/$(JENKINS_JOB_NAME)/$(JENKINS_BUILD_NUMBER)/arch=x86_64,build_type=server,distro=el6,ib_stack=inkernel/artifact/artifacts/RPMS/x86_64/
ALL_RPMS               = zfs-$(ZFS_RELEASE).el6.x86_64.rpm \
                         kmod-zfs-$(KERNEL_RELEASE)_lustre.x86_64-$(ZFS_RELEASE).el6.x86_64.rpm \
                         spl-$(ZFS_RELEASE).el6.x86_64.rpm \
                         kmod-spl-$(KERNEL_RELEASE)_lustre.x86_64-$(ZFS_RELEASE).el6.x86_64.rpm

NO_REQUIREMENT         = zfs spl kmod-spl-$(KERNEL_RELEASE)_lustre.x86_64 kmod-zfs-$(KERNEL_RELEASE)_lustre.x86_64

include ../include/Makefile.fetch-from-repo
