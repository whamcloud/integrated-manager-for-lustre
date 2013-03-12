BUILDER_IS_EL6 = $(shell rpm --eval '%{?el6:true}%{!?el6:false}')

# Top-level Makefile
SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

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
	set -e; \
	if $(BUILDER_IS_EL6); then \
		$(MAKE) -C $@ rpms; \
		$(MAKE) -C $@ docs; \
		if [ -d $@/dist/ ]; then \
			cp -a $@/dist/* dist/; \
		fi; \
	fi

rpms: $(SUBDIRS)

repo: rpms
	$(MAKE) -C chroma-dependencies repo

deps: repo
