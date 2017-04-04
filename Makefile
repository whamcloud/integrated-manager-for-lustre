BUILDER_IS_EL = $(shell rpm --eval '%{?rhel:true}%{!?rhel:false}')

# Top-level Makefile
SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

.PHONY: all rpms docs subdirs $(SUBDIRS) tags

all: TARGET=all
rpms: TARGET=rpms
docs: TARGET=docs
download: TARGET=download

all rpms docs download subdirs: $(SUBDIRS)

cleandist:
	rm -rf dist

dist: cleandist
	mkdir dist

agent:
	# On non-EL[67] builders, we'll only do an agent build
	$(BUILDER_IS_EL) || $(MAKE) -C chroma-agent $(TARGET)
	$(BUILDER_IS_EL) || cp -a chroma-agent/dist/* dist/

$(SUBDIRS): dist agent
	set -e; \
	if $(BUILDER_IS_EL); then \
		$(MAKE) -C $@ $(TARGET); \
		if [ $(TARGET) != download -a -d $@/dist/ ]; then \
			cp -a $@/dist/* dist/; \
		fi; \
	fi

repo: rpms
	$(MAKE) -C chroma-dependencies repo

bundles: repo
	$(MAKE) -C chroma-bundles

deps: repo

tags:
	#find chroma-agent/chroma_agent chroma-manager/{tests,chroma_{agent_comms,api,cli,core,ui}} -type f | ctags -L -
	ctags --python-kinds=-i -R --exclude=chroma-manager/_topdir --exclude=chroma-\*/myenv\* --exclude=chroma-dependencies --exclude=chroma_unit_test_env --exclude=chroma-externals --exclude=chroma-manager/chroma_ui* --exclude=chroma-manager/ui-modules .

# build the chroma-{agent,management} subdirs before the chroma-dependencies subdir
chroma-dependencies: chroma-agent chroma-manager chroma-diagnostics
chroma-bundles: chroma-dependencies
