include ../include/Makefile.lustre_build_meta

override REPO          := $(dir $(patsubst %/,%,$(REPO)))/repo-sles-server
RELEASE_POSTFIX        := _default$(UNDERSCORE_RELEASE_POSTFIX)
KERNEL_ARCH            = x86_64
KERNEL_RELEASE_MANGLED = $(subst -,_,$(LUSTRE_SLES_KERNEL_RELEASE))
CHROMA_EXTERNALS_SUBDIR := lustre
SRC_REPO               = $(JENKINS_ROOT_URL)/job/$(JENKINS_JOB_NAME)/$(JENKINS_BUILD_NUMBER)/arch=x86_64,build_type=server,distro=sles11sp3,ib_stack=inkernel/artifact/artifacts
ALL_RPMS               = lustre-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			 lustre-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			 lustre-osd-ldiskfs-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			 kernel-default-$(LUSTRE_SLES_KERNEL_RELEASE).$(KERNEL_ARCH).rpm \
			 kernel-default-base-$(LUSTRE_SLES_KERNEL_RELEASE).$(KERNEL_ARCH).rpm \
			 kernel-default-devel-$(LUSTRE_SLES_KERNEL_RELEASE).$(KERNEL_ARCH).rpm \
			 kernel-default-extra-$(LUSTRE_SLES_KERNEL_RELEASE).$(KERNEL_ARCH).rpm \
			 kernel-default-hmac-$(LUSTRE_SLES_KERNEL_RELEASE).$(KERNEL_ARCH).rpm \
			 kernel-source-$(LUSTRE_SLES_KERNEL_RELEASE).$(KERNEL_ARCH).rpm
NO_REQUIREMENT         = lustre lustre-modules lustre-osd-ldiskfs kernel-default kernel-default-base kernel-default-devel kernel-default-extra kernel-default-hmac kernel-source

include ../include/Makefile.fetch-from-repo
