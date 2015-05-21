DISTRO			:= el6.6
include ../include/Makefile.lustre_build_meta

LUSTRE_KERNEL_RELEASE	 = $(KERNEL_RELEASE)_lustre.x86_64
KERNEL_RELEASE_MANGLED	 = $(subst -,_,$(LUSTRE_KERNEL_RELEASE))

override REPO          := $(dir $(patsubst %/,%,$(REPO)))/repo-lustre

CHROMA_EXTERNALS_SUBDIR := lustre
SRC_REPO		 = $(JENKINS_ROOT_URL)/job/$(JENKINS_JOB_NAME)/$(JENKINS_BUILD_NUMBER)/arch=x86_64,build_type=server,distro=$(DISTRO),ib_stack=inkernel/artifact/artifacts
ALL_RPMS		 = lustre-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(UNDERSCORE_RELEASE_POSTFIX).x86_64.rpm \
			   lustre-dkms-$(LUSTRE_RELEASE)-1.el6.noarch.rpm \
			   lustre-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(UNDERSCORE_RELEASE_POSTFIX).x86_64.rpm \
			   lustre-osd-ldiskfs-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(UNDERSCORE_RELEASE_POSTFIX).x86_64.rpm \
			   lustre-osd-ldiskfs-mount-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(UNDERSCORE_RELEASE_POSTFIX).x86_64.rpm \
			   lustre-osd-zfs-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(UNDERSCORE_RELEASE_POSTFIX).x86_64.rpm \
			   lustre-osd-zfs-mount-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(UNDERSCORE_RELEASE_POSTFIX).x86_64.rpm \
			   kernel-$(LUSTRE_KERNEL_RELEASE).rpm \
			   kernel-firmware-$(LUSTRE_KERNEL_RELEASE).rpm \
			   kernel-headers-$(LUSTRE_KERNEL_RELEASE).rpm \
			   kernel-devel-$(LUSTRE_KERNEL_RELEASE).rpm
NO_REQUIREMENT		 = lustre lustre-dkms lustre-modules lustre-osd-ldiskfs lustre-osd-ldiskfs-mount lustre-osd-zfs lustre-osd-zfs-mount kernel kernel-firmware kernel-devel kernel-headers

include ../include/Makefile.fetch-from-repo
