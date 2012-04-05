# Top-level Makefile
SUBDIRS ?= $(shell find . -maxdepth 1 -mindepth 1 -type d -not -name '.*' -not -name dist -not -name scripts)

.PHONY: subdirs $(SUBDIRS)

subdirs: $(SUBDIRS)

cleandist:
	rm -rf dist

dist: cleandist
	mkdir dist

# This will go away when r3d is properly integrated into chroma-manager
r3d:
	$(MAKE) -C chroma-manager/r3d rpms
	cp -a chroma-manager/r3d/dist/* dist/

$(SUBDIRS): dist r3d
	$(MAKE) -C $@ rpms
	cp -a $@/dist/* dist/ || true
