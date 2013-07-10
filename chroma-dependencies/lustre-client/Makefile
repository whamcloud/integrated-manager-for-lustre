LUSTRE_RELEASE = 2.4.0
RELEASE_POSTFIX = .x86_64_gd3f91c4
KERNEL_RELEASE = 2.6.32-358.6.2.el6
KERNEL_RELEASE_MANGLED = $(subst -,_,$(KERNEL_RELEASE))
SRC_REPO = http://downloads.whamcloud.com/public/lustre/lustre-$(LUSTRE_RELEASE)/el6/client/RPMS/x86_64/

ALL_RPMS = lustre-client-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm lustre-client-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm lustre-client-source-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm 
NO_REQUIREMENT = lustre-client lustre-client-modules lustre-client-source

include ../include/Makefile.fetch-from-repo
