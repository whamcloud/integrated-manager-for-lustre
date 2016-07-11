ZFS_DISTRO=el6.8
TOP := $(CURDIR)
include $(TOP)/../include/Makefile.version
include $(TOP)/../chroma-dependencies/include/Makefile.zfs_version-$(ZFS_DISTRO)
REPO ?= $(TOP)/../chroma-dependencies/repo
WORKDIR := $(notdir $(CURDIR))
DISTRO := $(shell rpm --eval %dist | sed -e 's/\.\(el[0-9][0-9]*\).*/\1/')

PROFILES := default.profile base_managed_RH7.profile base_monitored.profile posix_copytool_worker.profile robinhood_server.profile
SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

all: package

clean: TARGET=clean
install: TARGET=install

.PHONY: subdirs $(SUBDIRS)

subdirs: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) TOP=$(TOP) REPO=$(REPO) -C $@ $(TARGET)

clean install:: subdirs

package: subdirs $(PROFILES) lesskey.out EULA.txt create_installer
	tar  --transform 's|$(WORKDIR)|$(SHORT_ARCHIVE_NAME)-$(ARCHIVE_VERSION)|' \
		$(foreach subdir,$(SUBDIRS),--transform 's|$(shell echo $(subdir)/*.tar.gz)|$(DISTRO)/$(notdir $(shell echo $(subdir)/*.tar.gz))|') \
		--show-transformed-names \
		-C ../ \
		--exclude README-INTERNAL \
	    -czvf $(SHORT_ARCHIVE_NAME)-$(ARCHIVE_VERSION).tar.gz $(WORKDIR)/create_installer $(WORKDIR)/install $(WORKDIR)/lesskey.out $(WORKDIR)/EULA.txt $(foreach profile,$(PROFILES),$(WORKDIR)/$(profile)) $(foreach subdir,$(SUBDIRS),$(WORKDIR)/$(shell echo $(subdir)/*.tar.gz))

lesskey.out: lesskey.in
	lesskey -o $@ $<

EULA.txt: ../chroma-manager/chroma_help/help.py
	python include/get_eula.py | html2text -o $@

rpms:
	@echo "I don't know how to make RPMS!"

docs download:
	@echo "Nothing to do here"

create_installer: create_installer.in $(TOP)/../chroma-dependencies/include/Makefile.zfs_version-$(ZFS_DISTRO)
	sed -e "s/@ZFS_VERSION@/$(ZFS_RELEASE)/" < $< > $@
	chmod 755 $@
