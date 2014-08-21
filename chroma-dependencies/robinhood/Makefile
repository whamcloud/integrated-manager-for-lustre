LOCATION := http://downloads.sourceforge.net/project/robinhood/robinhood/2.5.3/robinhood-2.5.3.tar.gz
REQUIREMENT :=
INSTALL_PKGS := robinhood-lhsm robinhood-adm robinhood-webgui
TARBALL_NOT_PYTHON := TRUE
RPM_OPTS := "--define '%lustre_source $(CURDIR)/lustre'"
LUSTRE_CLIENT_GLOB := $(CURDIR)/../lustre-client/lustre-client-[0-9]*.rpm

rpms: lustre/lustre/include

$(LUSTRE_CLIENT_GLOB):
	$(MAKE) -C ../lustre-client

lustre/lustre/include: $(LUSTRE_CLIENT_GLOB)
	rm -fr lustre
	mkdir -p lustre/lustre/include
	cd lustre && \
	rpm2cpio $(LUSTRE_CLIENT_GLOB) | cpio -id
	ln -s $(CURDIR)/lustre/usr/include/lustre lustre/lustre/include/lustre
	ln -s $(CURDIR)/lustre/usr/include/linux lustre/lustre/include/linux
	ln -s $(CURDIR)/lustre/usr/include/libcfs lustre/lustre/include/libcfs
	ln -s $(CURDIR)/lustre/usr/lib64 lustre/lustre/utils

include $(CURDIR)/../include/Makefile.rpm-from-tarball
