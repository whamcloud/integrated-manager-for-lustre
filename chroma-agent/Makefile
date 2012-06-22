
# The build number, for dev/test/support
BUILD := $(shell echo 1.0.0.0.`date -u +%Y%m%d%H%M`.`git rev-parse --short HEAD`)
# The A.B.C.D release number for releases, or a build number for test/dev builds
VERSION := $(BUILD)
# Flag for whether this is a release build
IS_RELEASE := False

ifeq ($(IS_RELEASE),True)
  PACKAGE_VERSION := $(VERSION)
else
  PACKAGE_VERSION := $(BUILD)
endif

PACKAGE_RELEASE := 2

all: rpms

version:
	echo 'VERSION = "$(VERSION)"' > chroma_agent/production_version.py
	echo 'BUILD = "$(BUILD)"' >> chroma_agent/production_version.py
	echo 'IS_RELEASE = $(IS_RELEASE)' >> chroma_agent/production_version.py
	echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"' >> chroma_agent/production_version.py

cleandist:
	rm -rf dist
	mkdir dist

production:
	
tarball: version
	rm -f MANIFEST
	python setup.py sdist

rpms: production cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/chroma-agent-*.tar.gz _topdir/SOURCES
	cp chroma-agent-init.sh _topdir/SOURCES
	cp chroma-agent.spec _topdir/SPECS
	rpmbuild --define "_topdir $$(pwd)/_topdir" \
		--define "version $(PACKAGE_VERSION)" \
		--define "release $(PACKAGE_RELEASE)" \
		-bb _topdir/SPECS/chroma-agent.spec
	mv _topdir/RPMS/noarch/chroma-agent-*.noarch.rpm dist/
	rm -rf _topdir

docs:
	@echo "Nothing to do here"
