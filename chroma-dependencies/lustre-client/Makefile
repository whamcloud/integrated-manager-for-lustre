LUSTRE_RELEASE = 2.5.1
RELEASE_POSTFIX = .x86_64
KERNEL_RELEASE = 2.6.32-431.5.1.el6
KERNEL_RELEASE_MANGLED = $(subst -,_,$(KERNEL_RELEASE))
SRC_REPO = https://jenkins-pull:Aitahd9u@build.whamcloud.com/job/lustre-b_ieel2_0/20/arch=x86_64,build_type=client,distro=el6,ib_stack=inkernel/artifact/artifacts/RPMS/x86_64/

ALL_RPMS = lustre-client-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm lustre-client-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm lustre-client-source-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm 
NO_REQUIREMENT = lustre-client lustre-client-modules lustre-client-source

include ../include/Makefile.fetch-from-repo
