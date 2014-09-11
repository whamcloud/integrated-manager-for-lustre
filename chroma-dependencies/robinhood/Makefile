include ../include/Makefile.lustre_build_meta

LOCATION := http://downloads.sourceforge.net/project/robinhood/robinhood/2.5.3/robinhood-2.5.3.tar.gz
REQUIREMENT :=
INSTALL_PKGS := robinhood-lhsm robinhood-adm robinhood-webgui
TARBALL_NOT_PYTHON := TRUE
RPM_OPTS := "--define '%lustre_source $(CURDIR)/lustre'"
RELEASE_POSTFIX = .x86_64

LUSTRE_INCLUDES = lustre/lustre/include/lustre/liblustreapi.h lustre/lustre/include/lustre/lustreapi.h lustre/lustre/include/lustre/lustre_idl.h

LUSTRE_CLIENT_RPM := $(TOP)/../chroma-externals/lustre-client-$(LUSTRE_RELEASE)-$(KERNEL_RELEASE_MANGLED)$(RELEASE_POSTFIX).x86_64.rpm

rpms: $(LUSTRE_INCLUDES)

$(LUSTRE_INCLUDES): $(LUSTRE_CLIENT_RPM)
	rm -fr lustre
	mkdir -p lustre/lustre/include
	cd lustre && \
	rpm2cpio $(LUSTRE_CLIENT_RPM) | cpio -id ./usr/include/\* ./usr/lib64/\*
	ln -s $(CURDIR)/lustre/usr/include/lustre lustre/lustre/include/lustre
	ln -s $(CURDIR)/lustre/usr/include/linux lustre/lustre/include/linux
	ln -s $(CURDIR)/lustre/usr/include/libcfs lustre/lustre/include/libcfs
	ln -s $(CURDIR)/lustre/usr/lib64 lustre/lustre/utils
	# force a rebuild of the robinhood RPMs
	touch robinhood.spec

include $(CURDIR)/../include/Makefile.rpm-from-tarball
