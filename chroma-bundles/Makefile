TOP := $(CURDIR)
include $(TOP)/../chroma-dependencies/include/Makefile.distro
include $(TOP)/../include/Makefile.version
include $(TOP)/../chroma-dependencies/include/Makefile.zfs_version-$(DISTRO)
REPO ?= $(TOP)/../chroma-dependencies/repo
WORKDIR := $(notdir $(CURDIR))

PROFILES := default.profile base_managed_RH7.profile base_monitored.profile posix_copytool_worker.profile robinhood_server.profile
SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

MFL_REPO_OWNER := $(firstword $(subst /, ,$(MFL_COPR_REPO)))
MFL_REPO_NAME := $(word 2,$(subst /, ,$(MFL_COPR_REPO)))

SUBSTS := chroma_support.repo

all: package

clean: TARGET=clean
install: TARGET=install

.PHONY: subdirs $(SUBDIRS)

subdirs: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) TOP=$(TOP) REPO=$(REPO) -C $@ $(TARGET)

clean install:: subdirs

chroma_support.repo: chroma_support.repo.in
	sed -e 's/@MFL_COPR_REPO@/$(subst /,\/,$(MFL_COPR_REPO))/g' \
	    -e 's/@MFL_REPO_OWNER@/$(MFL_REPO_OWNER)/g'             \
	    -e 's/@MFL_REPO_NAME@/$(MFL_REPO_NAME)/g' < $< > $@

package: subdirs $(PROFILES) lesskey.out create_installer chroma_support.repo
	tar  --transform 's|$(WORKDIR)|$(SHORT_ARCHIVE_NAME)-$(ARCHIVE_VERSION)|' \
		$(foreach subdir,$(SUBDIRS),--transform 's|$(shell echo $(subdir)/*.tar.gz)|$(DISTRO_TAG)/$(notdir $(shell echo $(subdir)/*.tar.gz))|') \
		--show-transformed-names \
		-C ../ \
		--exclude README-INTERNAL \
	    -czvf $(SHORT_ARCHIVE_NAME)-$(ARCHIVE_VERSION).tar.gz $(WORKDIR)/chroma_support.repo $(WORKDIR)/create_installer $(WORKDIR)/install $(WORKDIR)/lesskey.out $(foreach profile,$(PROFILES),$(WORKDIR)/$(profile)) $(foreach subdir,$(SUBDIRS),$(WORKDIR)/$(shell echo $(subdir)/*.tar.gz))

lesskey.out: lesskey.in
	lesskey -o $@ $<

rpms:
	@echo "I don't know how to make RPMS!"

docs download:
	@echo "Nothing to do here"

substs: $(SUBSTS)

clean_substs:
	if [ -n "$(SUBSTS)" ]; then \
	    rm -f $(SUBSTS);        \
	fi

.PHONY: substs
