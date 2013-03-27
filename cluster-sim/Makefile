include ../include/Makefile.version

all: rpms

cleandist:
	rm -rf dist
	mkdir dist

version:
	echo 'VERSION = "$(VERSION)"' > cluster_sim/scm_version.py
	echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"' >> cluster_sim/scm_version.py
	echo 'BUILD = $(BUILD_NUMBER)' >> cluster_sim/scm_version.py
	echo 'IS_RELEASE = $(IS_RELEASE)' >> cluster_sim/scm_version.py

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

docs:
	@echo "Nothing to do here"
