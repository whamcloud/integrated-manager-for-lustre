include ../include/Makefile.lustre_build_meta

RELEASE_POSTFIX := .x86_64$(UNDERSCORE_RELEASE_POSTFIX)
CHROMA_EXTERNALS_SUBDIR := lustre
SRC_REPO = $(JENKINS_ROOT_URL)/job/$(JENKINS_JOB_NAME)/$(JENKINS_BUILD_NUMBER)/arch=x86_64,build_type=client,distro=$(EL_BUILDER_DISTRO),ib_stack=inkernel/artifact/artifacts

ALL_RPMS = lustre-client-$(LUSTRE_RELEASE)-$(EL_KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
	   lustre-client-modules-$(LUSTRE_RELEASE)-$(EL_KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
	   lustre-client-source-$(LUSTRE_RELEASE)-$(EL_KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm
NO_REQUIREMENT = lustre-client lustre-client-modules lustre-client-source lustre-dkms

include ../include/Makefile.fetch-from-repo
