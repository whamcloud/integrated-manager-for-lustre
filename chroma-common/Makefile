include ../include/Makefile.version

ARCH := $(shell echo $$(uname -m))

all: rpms

cleandist:
	rm -rf dist
	mkdir dist

version:
	echo 'VERSION = "$(VERSION)"' > chroma_common/scm_version.py
	echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"' >> chroma_common/scm_version.py
	echo 'BUILD = "$(BUILD_NUMBER)"' >> chroma_common/scm_version.py
	echo 'IS_RELEASE = $(IS_RELEASE)' >> chroma_common/scm_version.py

develop: version
	python setup.py develop

tarball: version
	rm -f MANIFEST
	python setup.py sdist

rpms: cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/$(ARCH)}
	cp dist/chroma-common-$(PACKAGE_VERSION).tar.gz _topdir/SOURCES
	cp chroma-common.spec _topdir/SPECS
	dist=$$(rpm --eval %dist);                             \
	dist=$${dist/.centos/};                                \
	rpmbuild --define "_topdir $$(pwd)/_topdir" 		   \
		--define "version $(PACKAGE_VERSION)" 		  \
		--define "package_release $(PACKAGE_RELEASE)" \
		--define "%dist $$dist"                       \
		-bb _topdir/SPECS/chroma-common.spec
	mv _topdir/RPMS/$(ARCH)/chroma-common-*$(PACKAGE_VERSION)-$(PACKAGE_RELEASE)$$(rpm --eval %{dist} | sed -e 's/\(\.el[0-9][0-9]*\)\.centos/\1/').$(ARCH).rpm dist/
	rm -rf _topdir

docs download:
	@echo "Nothing to do here"
