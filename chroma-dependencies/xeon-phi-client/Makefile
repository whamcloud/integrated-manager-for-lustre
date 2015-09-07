DISTRO			:= el6.7
include ../include/Makefile.lustre_build_meta

override REPO		:= $(dir $(patsubst %/,%,$(REPO)))/repo-xeon-phi-client
RELEASE_POSTFIX		:= +mpss3.4.3$(UNDERSCORE_RELEASE_POSTFIX)
KERNEL_RELEASE		= 2.6.38.8
KERNEL_RELEASE_MANGLED	= $(subst -,_,$(KERNEL_RELEASE))
CHROMA_EXTERNALS_SUBDIR := lustre
SRC_REPO		= $(JENKINS_ROOT_URL)/job/$(JENKINS_JOB_NAME)/$(JENKINS_BUILD_NUMBER)/arch=xeonphi,build_type=client,distro=$(DISTRO),ib_stack=inkernel/artifact/artifacts

ALL_RPMS		= lustre-client-mic-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			  lustre-client-mic-modules-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm \
			  lustre-client-mic-source-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm 
NO_REQUIREMENT		= lustre-client-mic lustre-client-mic-modules lustre-client-mic-source

include ../include/Makefile.fetch-from-repo
