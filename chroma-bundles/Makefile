TOP := $(CURDIR)
REPO ?= $(TOP)/../chroma-dependencies/repo

SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

all: package

clean: TARGET=clean
install: TARGET=install

.PHONY: subdirs $(SUBDIRS)

subdirs: $(SUBDIRS)

$(SUBDIRS):
	$(MAKE) TOP=$(TOP) REPO=$(REPO) -C $@ $(TARGET)

clean install:: subdirs

package: subdirs
	tar --transform 's|.*/||' --show-transformed-names \
	    -czvf chroma.tar.gz install.sh $(patsubst %,%/*.tar.gz,$(SUBDIRS))

rpms:
	@echo "I don't know how to make RPMS!"

docs:
	@echo "Nothing to do here"
