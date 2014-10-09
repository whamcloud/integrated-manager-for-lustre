include ../include/Makefile.lustre_build_meta

override REPO		:= $(dir $(patsubst %/,%,$(REPO)))/repo-sles-client
RELEASE_POSTFIX		:= _default$(UNDERSCORE_RELEASE_POSTFIX)
KERNEL_RELEASE		= 3.0.101-0.35
KERNEL_RELEASE_MANGLED	= $(subst -,_,$(KERNEL_RELEASE))
CHROMA_EXTERNALS_SUBDIR := lustre
SRC_REPO		= $(JENKINS_ROOT_URL)/job/$(JENKINS_JOB_NAME)/$(JENKINS_BUILD_NUMBER)/arch=x86_64,build_type=client,distro=sles11sp3,ib_stack=inkernel/artifact/artifacts/RPMS/x86_64/

ALL_RPMS		= lustre-client-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			  lustre-client-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			  lustre-client-source-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm 
NO_REQUIREMENT		= lustre-client lustre-client-modules lustre-client-source

include ../include/Makefile.fetch-from-repo
