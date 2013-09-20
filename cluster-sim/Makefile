include ../include/Makefile.version

FENCE_AGENTS_URL	:= http://vault.centos.org/6.4/os/x86_64/Packages/fence-agents-3.1.5-25.el6.x86_64.rpm
FENCE_AGENTS_RPM	:= $(shell basename $(FENCE_AGENTS_URL))
FENCE_APC			:= $(shell if which fence_apc 2>/dev/null; then true; else echo $(word 1,$(subst :, ,$(PATH)))/fence_apc; fi)
RPM2CPIO			:= $(shell if which rpm2cpio 2>/dev/null; then true; else echo rpm2cpio; fi)

all: rpms

cleandist:
	rm -rf dist
	mkdir dist

version:
	echo 'VERSION = "$(VERSION)"' > cluster_sim/scm_version.py
	echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"' >> cluster_sim/scm_version.py
	echo 'BUILD = "$(BUILD_NUMBER)"' >> cluster_sim/scm_version.py
	echo 'IS_RELEASE = $(IS_RELEASE)' >> cluster_sim/scm_version.py

develop: version $(FENCE_APC)
	python setup.py develop

tarball: version
	rm -f MANIFEST
	python setup.py sdist

rpms: cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/chroma-cluster-sim-*.tar.gz _topdir/SOURCES
	cp chroma-cluster-sim.spec _topdir/SPECS
	rpmbuild --define "_topdir $$(pwd)/_topdir" \
		--define "version $(PACKAGE_VERSION)" \
		--define "release $(PACKAGE_RELEASE)" \
		-bb _topdir/SPECS/chroma-cluster-sim.spec
	mv _topdir/RPMS/noarch/chroma-cluster-sim-*.noarch.rpm dist/
	rm -rf _topdir

docs download:
	@echo "Nothing to do here"

$(RPM2CPIO):
	@echo "You need to install $@ first... (brew install $@?)"
	exit 1

$(FENCE_APC): $(RPM2CPIO)
	tmpdir=$$(mktemp -d -t fence.XXXX); \
	venv=$$(dirname $$(dirname $(FENCE_APC))); \
	cd $$tmpdir && curl -o $(FENCE_AGENTS_RPM) $(FENCE_AGENTS_URL); \
	rpm2cpio $(FENCE_AGENTS_RPM) | cpio -id; \
	mkdir -p $$venv/share/fence && cp usr/share/fence/*.py $$venv/share/fence; \
	sed -e "s/\(print o + options\[\"-C\"\] + alias\)/\1 + options[\"-C\"] + status/" \
		< usr/share/fence/fencing.py > $$venv/share/fence/fencing.py; \
	cp usr/sbin/$$(basename $(FENCE_APC)) $(FENCE_APC); \
	sed -e "s:/usr/share/fence:$$venv/share/fence:" \
	    -e "s:/usr/bin/python:/usr/bin/env python:" \
		< $(FENCE_APC) > $(FENCE_APC).new; \
	mv $(FENCE_APC).new $(FENCE_APC); chmod +x $(FENCE_APC); \
	rm -fr $$tmpdir

# This target will cause a fence-agents RPM to be downloaded and torn apart
# so that fence_apc is available in a development environment.
fence_agents: $(FENCE_APC)
