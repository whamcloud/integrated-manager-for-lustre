BUILDER_IS_EL6 = $(shell rpm --eval '%{?el6:true}%{!?el6:false}')

# Top-level Makefile
SUBDIRS ?= $(shell find . -maxdepth 1 -mindepth 1 -type d -not -name '.*' -not -name dist -not -name scripts)

.PHONY: subdirs $(SUBDIRS)

subdirs: $(SUBDIRS)

cleandist:
	rm -rf dist

dist: cleandist
	mkdir dist

agent:
	# On non-EL6 builders, we'll only do an agent build
	$(BUILDER_IS_EL6) || $(MAKE) -C chroma-agent rpms
	$(BUILDER_IS_EL6) || $(MAKE) -C chroma-agent docs
	$(BUILDER_IS_EL6) || cp -a chroma-agent/dist/* dist/

$(SUBDIRS): dist agent
	# We only do a full build on EL6
	if $(BUILDER_IS_EL6); then \
		$(MAKE) -C $@ rpms; \
		$(MAKE) -C $@ docs; \
		cp -a $@/dist/* dist/; \
	fi

rpms: $(SUBDIRS)
