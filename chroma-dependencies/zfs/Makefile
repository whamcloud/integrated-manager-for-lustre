include ../include/Makefile.lustre_build_meta

ZFS_RELEASE		:= 0.6.3-1.1

CHROMA_EXTERNALS_SUBDIR := zfs
SRC_REPO		:= $(JENKINS_ROOT_URL)/job/$(JENKINS_JOB_NAME)/$(JENKINS_BUILD_NUMBER)/arch=x86_64,build_type=server,distro=$(EL_BUILDER_DISTRO),ib_stack=inkernel/artifact/artifacts
ALL_RPMS		:= zfs-$(ZFS_RELEASE).el6.x86_64.rpm \
			   zfs-$(ZFS_RELEASE).el6.src.rpm \
			   kmod-zfs-$(LUSTRE_EL_KERNEL_RELEASE)-$(ZFS_RELEASE).el6.x86_64.rpm \
			   zfs-dkms-$(ZFS_RELEASE).el6.noarch.rpm \
			   spl-$(ZFS_RELEASE).el6.x86_64.rpm \
			   spl-$(ZFS_RELEASE).el6.src.rpm \
			   spl-dkms-$(ZFS_RELEASE).el6.noarch.rpm \
			   kmod-spl-$(LUSTRE_EL_KERNEL_RELEASE)-$(ZFS_RELEASE).el6.x86_64.rpm \
			   libnvpair1-$(ZFS_RELEASE).el6.x86_64.rpm \
			   libuutil1-$(ZFS_RELEASE).el6.x86_64.rpm \
			   libzfs2-$(ZFS_RELEASE).el6.x86_64.rpm \
			   libzpool2-$(ZFS_RELEASE).el6.x86_64.rpm

NO_REQUIREMENT		:= zfs zfs-dkms spl spl-dkms kmod-spl-$(LUSTRE_EL_KERNEL_RELEASE) kmod-zfs-$(LUSTRE_EL_KERNEL_RELEASE) \
-			   libnvpair1 libuutil1 libzfs2 libzpool2

include ../include/Makefile.fetch-from-repo

# we don't actually want to do anything with these SRPMS except download
# it to chroma-externals
all rpms $(SPECNAME):
	echo "Nothing to do here for $@"
