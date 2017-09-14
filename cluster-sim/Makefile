include ../chroma-dependencies/include/Makefile.distro
include ../include/Makefile.version

ifeq ($(DISTRO_TAG), el6)
	FENCE_AGENTS_URL    := http://vault.centos.org/6.4/os/x86_64/Packages/fence-agents-3.1.5-25.el6.x86_64.rpm
else ifeq ($(DISTRO_TAG), el7)
	FENCE_AGENTS_URL    := http://mirror.centos.org/centos-7/7/os/x86_64/Packages/fence-agents-{common,apc}-4.0.11-66.el7.x86_64.rpm
else
	$(error "Unknown major distro version $(DISTRO_TAG)")
endif
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
	echo "jenkins_fold:start:Make Simulator Tarball"
	rm -f MANIFEST
	python setup.py sdist
	echo "jenkins_fold:end:Make Simulator Tarball"

rpms: cleandist tarball
	echo "jenkins_fold:start:Make Simulator RPMS"
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/chroma-cluster-sim-*.tar.gz _topdir/SOURCES
	cp chroma-cluster-sim.spec _topdir/SPECS
	rpmbuild --define "_topdir $$(pwd)/_topdir" \
		--define "version $(PACKAGE_VERSION)" \
		--define "package_release $(PACKAGE_RELEASE)" \
		-bb _topdir/SPECS/chroma-cluster-sim.spec
	mv _topdir/RPMS/noarch/chroma-cluster-sim-*.noarch.rpm dist/
	rm -rf _topdir
	echo "jenkins_fold:end:Make Simulator RPMS"

docs download:
	echo $(FENCE_AGENTS_URL)
	@echo "Nothing to do here"

$(RPM2CPIO):
	@echo "You need to install $@ first... (brew install $@?)"
	exit 1

# Retrieve required fence-agent rpms, extract fencing.py and
# fence_apc scripts and install into python virtual env used
# by manager. Different rpms required in el6/el7 distros.
$(FENCE_APC): $(RPM2CPIO)
	echo "Distro: $(DISTRO)"
	set -e; \
	tmpdir=$$(mktemp -d -t fence.XXXX); \
	venv=$$(dirname $$(dirname $(FENCE_APC))); \
	cd $$tmpdir && curl --remote-name-all $(FENCE_AGENTS_URL); \
	for rpm in $$(ls *.rpm); do \
		echo "Unpacking: $$rpm"; \
		rpm2cpio $$rpm | cpio -id; \
	done; \
	mkdir -p $$venv/share/fence && cp usr/share/fence/*.py $$venv/share/fence; \
	sed -e "s/\(print o + options\[\"-C\"\] + alias\)/\1 + options[\"-C\"] + status/" \
		< usr/share/fence/fencing.py > $$venv/share/fence/fencing.py; \
	cp usr/sbin/$$(basename $(FENCE_APC)) $(FENCE_APC); \
	sed -e "s:/usr/share/fence:$$venv/share/fence:" \
	    -e "s:/usr/bin/python.*:/usr/bin/env python:" \
		< $(FENCE_APC) > $(FENCE_APC).new; \
	mv $(FENCE_APC).new $(FENCE_APC); chmod +x $(FENCE_APC); \
	rm -fr $$tmpdir

# This target will cause a fence-agents RPM to be downloaded and torn apart
# so that fence_apc is available in a development environment.
fence_agents: $(FENCE_APC)

print-%: ; @$(error $* is $($*) ($(value $*)) (from $(origin $*)))
