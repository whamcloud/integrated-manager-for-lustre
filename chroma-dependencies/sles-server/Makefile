DISTRO			:= sles11sp3
include ../include/Makefile.lustre_build_meta

# ~sigh~  SUSE, why do you have to make things so difficult?
KERNEL_RELEASE		:= $(subst -default,,$(KERNEL_RELEASE))

LUSTRE_KERNEL_RELEASE = $(KERNEL_RELEASE)_lustre

override REPO          := $(dir $(patsubst %/,%,$(REPO)))/repo-sles-server
RELEASE_POSTFIX		:= _default$(UNDERSCORE_RELEASE_POSTFIX)
KERNEL_ARCH		 = x86_64
KERNEL_RELEASE_MANGLED	 = $(subst -,_,$(LUSTRE_KERNEL_RELEASE))
CHROMA_EXTERNALS_SUBDIR	:= lustre
SRC_REPO		 = $(JENKINS_ROOT_URL)/job/$(JENKINS_JOB_NAME)/$(JENKINS_BUILD_NUMBER)/arch=x86_64,build_type=server,distro=sles11sp3,ib_stack=inkernel/artifact/artifacts
ALL_RPMS		 = lustre-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			   lustre-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			   lustre-osd-ldiskfs-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			   kernel-default-$(LUSTRE_KERNEL_RELEASE).$(KERNEL_ARCH).rpm \
			   kernel-default-base-$(LUSTRE_KERNEL_RELEASE).$(KERNEL_ARCH).rpm \
			   kernel-default-devel-$(LUSTRE_KERNEL_RELEASE).$(KERNEL_ARCH).rpm \
			   kernel-default-extra-$(LUSTRE_KERNEL_RELEASE).$(KERNEL_ARCH).rpm \
			   kernel-default-hmac-$(LUSTRE_KERNEL_RELEASE).$(KERNEL_ARCH).rpm \
			   kernel-source-$(LUSTRE_KERNEL_RELEASE).$(KERNEL_ARCH).rpm
NO_REQUIREMENT		 = lustre lustre-modules lustre-osd-ldiskfs kernel-default kernel-default-base \
			   kernel-default-devel kernel-default-extra kernel-default-hmac kernel-source

include ../include/Makefile.fetch-from-repo
