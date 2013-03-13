TOP ?= $(shell while [[ $$PWD != */chroma-dependencies ]]; do cd ..; done; echo $$PWD)
include $(TOP)/include/Makefile.meta
REPO = $(TOP)/repo/

SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

all: repo

.PHONY: rpms clean distclean install
rpms clean distclean install:: $(SUBDIRS)

rpms: TARGET=rpms
clean: TARGET=clean
distclean: TARGET=distclean
install: TARGET=install

$(SUBDIRS): cleanrepo force
	$(MAKE) TOP=$(TOP) REPO=$(REPO) -C $@ $(TARGET)

cleanrepo:
	if [ $(TARGET) = install ]; then \
		rm -rf $(REPO);          \
		mkdir $(REPO);           \
	fi
.PHONY: force
force :;

repo: install
	cd $(REPO); \
	createrepo --pretty .

FORCE:

docs:
	@echo "Nothing to do here"
