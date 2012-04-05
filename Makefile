# Top-level Makefile
SUBDIRS ?= $(shell find . -maxdepth 1 -mindepth 1 -type d -not -name '.*' -not -name dist -not -name scripts)

.PHONY: subdirs $(SUBDIRS)

subdirs: $(SUBDIRS)

cleandist:
	rm -rf dist

dist: cleandist
	mkdir dist

$(SUBDIRS): dist
	$(MAKE) -C $@ rpms
	cp -a $@/dist/* dist/ || true
