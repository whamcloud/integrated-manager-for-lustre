TOP ?= $(shell while [[ $$PWD != */chroma-dependencies ]]; do cd ..; done; echo $$PWD)
include $(TOP)/include/Makefile.meta

TARBALL_EXT		?= tar.gz
TARBALL_NAME	:= mod_proxy_wstunnel
TARBALL_VERSION	:= 0.1
TARBALL			:= $(TARBALL_NAME)-$(TARBALL_VERSION).$(TARBALL_EXT)
SPECNAME		?= $(TARBALL_NAME).spec

# Flag to indicate which type of build should occur
BUILD_TYPE		?= REPO

# For a repo build, run through the usual chroma-dependencies process.
ifeq ($(BUILD_TYPE),REPO)
rpms: $(SPECNAME) $(TARBALL)
	$(MAKE) -f ../include/Makefile.rpmbuild $@

install pkg_install: rpms
	$(MAKE) -f ../include/Makefile.install INSTALL_PKGS="$(INSTALL_PKGS)" SPECFILE="$(SPECNAME)" $@

requirements:
	@echo ""

$(TARBALL): src/*.c src/*.h *.patch
	tar --transform 's|src|$(TARBALL_NAME)-$(TARBALL_VERSION)|' \
		-czvf $(TARBALL) src/*

clean:
	rm -f $(TARBALL)
	$(MAKE) -f ../include/Makefile.rpmbuild clean
endif

# A DEVEL build occurs when this makefile is called via 'make develop'. In
# this case, the module should be built and installed for use by the
# devel-mode httpd.
ifeq ($(BUILD_TYPE),DEVEL)
CC_BIN			:= $(shell if which cc 2>/dev/null; then true; else echo cc; fi)
DEV_BUILD_DIR	:= $(CURDIR)/dev_build
DEV_HTTPD_DEST	:= $(TOP)/../chroma-manager/dev_httpd
MODULE_SO_FILE	:= $(TARBALL_NAME).so
BUILT_SO		:= $(DEV_BUILD_DIR)/.libs/$(MODULE_SO_FILE)
INSTALLED_SO	:= $(DEV_HTTPD_DEST)/$(MODULE_SO_FILE)

install: $(INSTALLED_SO)
	@echo
	@echo
	@echo Successfully installed $(INSTALLED_SO). Your development \
		  httpd should now be able to use $(TARBALL_NAME).
	@echo
	@echo Hint: Configure $(dir $(DEV_HTTPD_DEST))chroma-manager.conf.template

build: $(BUILT_SO)

clean:
	rm -fr $(DEV_BUILD_DIR)
	rm -f $(INSTALLED_SO)

$(DEV_BUILD_DIR):
	mkdir -p $@

$(BUILT_SO): $(CC_BIN) src/*.c src/*.h *.patch $(DEV_BUILD_DIR)
	cp -a src/* $(DEV_BUILD_DIR)
	cd $(DEV_BUILD_DIR); \
	for patch in $(CURDIR)/*.patch; do \
		patch -p1 < $$patch; \
	done
	cd $(DEV_BUILD_DIR); \
	./configure
	$(MAKE) -C $(DEV_BUILD_DIR)

$(INSTALLED_SO): $(BUILT_SO)
	cp -a $(BUILT_SO) $(INSTALLED_SO)

$(CC_BIN):
	@echo Unable to find $@. Is XCode correctly installed?
	exit 1
endif
