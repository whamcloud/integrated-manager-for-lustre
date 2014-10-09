TOP := $(CURDIR)
include $(TOP)/../include/Makefile.version
REPO ?= $(TOP)/../chroma-dependencies/repo
WORKDIR := $(notdir $(CURDIR))

PROFILES := default.profile base_managed.profile base_monitored.profile posix_copytool_worker.profile robinhood_server.profile
SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')
HADOOPDIR = chroma-externals/hadoop

all: package

clean: TARGET=clean
install: TARGET=install

.PHONY: subdirs $(SUBDIRS)

subdirs: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) TOP=$(TOP) REPO=$(REPO) -C $@ $(TARGET)

clean install:: subdirs

package: subdirs $(PROFILES) lesskey.out EULA.txt
	tar  --transform 's|$(WORKDIR)|$(SHORT_ARCHIVE_NAME)-$(ARCHIVE_VERSION)|' \
		$(foreach subdir,$(SUBDIRS),--transform 's|$(shell echo $(subdir)/*.tar.gz)|$(notdir $(shell echo $(subdir)/*.tar.gz))|') \
		--transform 's|$(HADOOPDIR)|hadoop|' \
		--show-transformed-names \
		-C ../ \
	    -czvf $(SHORT_ARCHIVE_NAME)-$(ARCHIVE_VERSION).tar.gz $(WORKDIR)/create_installer $(WORKDIR)/install $(WORKDIR)/lesskey.out $(WORKDIR)/EULA.txt $(foreach profile,$(PROFILES),$(WORKDIR)/$(profile)) $(foreach subdir,$(SUBDIRS),$(WORKDIR)/$(shell echo $(subdir)/*.tar.gz)) $(TOP)/../$(HADOOPDIR)/*

lesskey.out: lesskey.in
	lesskey -o $@ $<

EULA.txt: ../chroma-manager/chroma_help/help.py
	python include/get_eula.py | html2text -o $@

rpms:
	@echo "I don't know how to make RPMS!"

docs download:
	@echo "Nothing to do here"
