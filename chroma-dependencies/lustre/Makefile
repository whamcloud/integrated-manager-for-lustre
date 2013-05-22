LUSTRE_RELEASE = 2.3.0
RELEASE_POSTFIX = .gb16fe80
KERNEL_RELEASE = 2.6.32-279.5.1.el6
KERNEL_RELEASE_MANGLED = $(subst -,_,$(KERNEL_RELEASE))
LDISKFS_RELEASE = 3.3.0
SRC_REPO = http://downloads.whamcloud.com/public/lustre/lustre-$(LUSTRE_RELEASE)/el6/server/RPMS/x86_64/

ALL_RPMS = lustre-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)_lustre$(RELEASE_POSTFIX).x86_64.x86_64.rpm lustre-ldiskfs-$(LDISKFS_RELEASE)-$(KERNEL_RELEASE_MANGLED)_lustre$(RELEASE_POSTFIX).x86_64.x86_64.rpm lustre-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)_lustre$(RELEASE_POSTFIX).x86_64.x86_64.rpm kernel-$(KERNEL_RELEASE)_lustre$(RELEASE_POSTFIX).x86_64.rpm kernel-firmware-$(KERNEL_RELEASE)_lustre$(RELEASE_POSTFIX).x86_64.rpm
NO_REQUIREMENT = lustre lustre-ldiskfs lustre-modules kernel kernel-firmware

include ../include/Makefile.fetch-from-repo
