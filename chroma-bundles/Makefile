TOP := $(CURDIR)
REPO ?= $(TOP)/../chroma-dependencies/repo

SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

all: TARGET=all
clean: TARGET=clean
install: TARGET=install

.PHONY: subdirs $(SUBDIRS)

subdirs: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) TOP=$(TOP) REPO=$(REPO) -C $@ $(TARGET)

all clean install:: subdirs

rpms:
	@echo "I don't know how to make RPMS!"

docs:
	@echo "Nothing to do here"
