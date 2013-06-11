TOP := $(CURDIR)
include $(TOP)/../include/Makefile.version
REPO ?= $(TOP)/../chroma-dependencies/repo
WORKDIR := $(notdir $(CURDIR))

PROFILES := base_managed.profile
SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

all: package

clean: TARGET=clean
install: TARGET=install

.PHONY: subdirs $(SUBDIRS)

subdirs: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) TOP=$(TOP) REPO=$(REPO) -C $@ $(TARGET)

clean install:: subdirs

%.profile: %.profile.template $(patsubst %,%/repo/meta,$(SUBDIRS))
	include/make_profile $@ $(subst chroma-manager/repo/meta,,$^)

package: subdirs $(PROFILES)
	tar  --transform 's|$(WORKDIR)|$(SHORT_ARCHIVE_NAME)-$(ARCHIVE_VERSION)|' \
		$(foreach subdir,$(SUBDIRS),--transform 's|$(shell echo $(subdir)/*.tar.gz)|$(notdir $(shell echo $(subdir)/*.tar.gz))|') \
		--show-transformed-names \
		-C ../ \
	    -czvf $(SHORT_ARCHIVE_NAME)-$(ARCHIVE_VERSION).tar.gz $(WORKDIR)/install $(foreach profile,$(PROFILES),$(WORKDIR)/$(profile)) $(foreach subdir,$(SUBDIRS),$(WORKDIR)/$(shell echo $(subdir)/*.tar.gz))

rpms:
	@echo "I don't know how to make RPMS!"

docs:
	@echo "Nothing to do here"
