include ../include/Makefile.lustre_build_meta

override REPO          := $(dir $(patsubst %/,%,$(REPO)))/repo-lustre
RELEASE_POSTFIX        =
KERNEL_RELEASE         = 2.6.32-431.5.1.el6_lustre.x86_64
KERNEL_RELEASE_MANGLED = $(subst -,_,$(KERNEL_RELEASE))
SRC_REPO               = $(JENKINS_ROOT_URL)/job/$(JENKINS_JOB_NAME)/$(JENKINS_BUILD_NUMBER)/arch=x86_64,build_type=server,distro=el6,ib_stack=inkernel/artifact/artifacts/RPMS/x86_64/
ALL_RPMS               = lustre-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			 lustre-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			 lustre-osd-ldiskfs-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			 kernel-$(KERNEL_RELEASE).rpm \
			 kernel-firmware-$(KERNEL_RELEASE).rpm \
			 kernel-headers-$(KERNEL_RELEASE).rpm \
			 kernel-devel-$(KERNEL_RELEASE).rpm
NO_REQUIREMENT         = lustre lustre-modules lustre-osd-ldiskfs kernel kernel-firmware kernel-devel kernel-headers

include ../include/Makefile.fetch-from-repo
