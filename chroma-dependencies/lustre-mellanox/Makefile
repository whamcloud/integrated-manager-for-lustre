override REPO          := $(dir $(patsubst %/,%,$(REPO)))/repo-lustre-mellanox
LUSTRE_RELEASE         = 2.3.11
RELEASE_POSTFIX        = _g870ed4e
KERNEL_RELEASE         = 2.6.32-358.6.2.el6_lustre.g54c1199.x86_64
KERNEL_RELEASE_MANGLED = $(subst -,_,$(KERNEL_RELEASE))
LDISKFS_RELEASE        = 3.4.1
SRC_REPO               = https://jenkins-pull:Aitahd9u@build.whamcloud.com/job/lustre-chris-reviews/79/arch=x86_64,build_type=server,distro=el6,ib_stack=ofa/artifact/artifacts/RPMS/x86_64/
ALL_RPMS               = lustre-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			 lustre-ldiskfs-$(LDISKFS_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			 lustre-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			 kernel-$(KERNEL_RELEASE).rpm \
			 kernel-ib-2.0-$(KERNEL_RELEASE_MANGLED)_OFED.2.0.2.0.5.g1593535.x86_64.rpm \
			 kernel-firmware-$(KERNEL_RELEASE).rpm
NO_REQUIREMENT         = lustre lustre-ldiskfs lustre-modules kernel kernel-firmware kernel-ib

include ../include/Makefile.fetch-from-repo
