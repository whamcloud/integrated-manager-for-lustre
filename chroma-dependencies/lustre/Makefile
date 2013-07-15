LUSTRE_RELEASE = 2.3.11
RELEASE_POSTFIX = 
KERNEL_RELEASE = 2.6.32-358.11.1.el6_lustre.x86_64
KERNEL_RELEASE_MANGLED = $(subst -,_,$(KERNEL_RELEASE))
LDISKFS_RELEASE = 3.4.1
SRC_REPO = https://jenkins-pull:Aitahd9u@build.whamcloud.com/job/lustre-chris/28/arch=x86_64,build_type=server,distro=el6,ib_stack=inkernel/artifact/artifacts/RPMS/x86_64/
ALL_RPMS = lustre-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm lustre-ldiskfs-$(LDISKFS_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm lustre-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm kernel-$(KERNEL_RELEASE)$(RELEASE_POSTFIX).rpm kernel-firmware-$(KERNEL_RELEASE)$(RELEASE_POSTFIX).rpm
NO_REQUIREMENT = lustre lustre-ldiskfs lustre-modules kernel kernel-firmware

include ../include/Makefile.fetch-from-repo
