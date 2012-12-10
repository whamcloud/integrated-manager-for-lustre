
# The build number, for dev/test/support
BUILD := $(shell echo 1.0.1.0.`date -u +%Y%m%d%H%M`.`git rev-parse --short HEAD`)
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

# In development, we want to stop at first failure, but when running
# in a Jenkins job we want all the gory details.
ifdef JENKINS_URL
	BEHAVE_ARGS ?= --junit --junit-directory $$WORKSPACE/test_reports --format plain
	NOSE_ARGS ?= --with-xunit --xunit-file=$WORKSPACE/test_reports/chroma-manager-unit-test-results.xml
else
	BEHAVE_ARGS ?= -q --stop
	NOSE_ARGS ?=
endif

cleandist:
	rm -rf  dist
	mkdir dist

version:
	echo 'VERSION = "$(VERSION)"' > production_version.py
	echo 'BUILD = "$(BUILD)"' >> production_version.py
	echo 'IS_RELEASE = $(IS_RELEASE)' >> production_version.py
	echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"' >> production_version.py

develop: version
	python setup.py develop

unit_tests:
	rm -f unit.log
	@echo "Running standard unit tests..."
	@./manage.py test $(NOSE_ARGS) 2>&1 | tee unit.log; \
	exit $${PIPESTATUS[0]}

feature_tests:
	@echo "Running behave features tests..."
	@for feature in tests/feature/*; do \
		logname=feature-$$(basename $$feature); \
		stdout=$$logname.stdout; stderr=$$logname.stderr; \
		rm -f $$stdout $$stderr; \
		behave $(BEHAVE_ARGS) $${feature}/features 2>$$stderr | tee $$stdout; \
		brc=$${PIPESTATUS[0]}; \
		[ $$brc -eq 0 ] || { \
			echo "$$feature failed, logs: $$stdout, $$stderr"; \
	        break; \
		} && true; \
	done; \
	exit $$brc

test: unit_tests feature_tests

tarball: version
	rm -f MANIFEST
	sed -e 's/@VERSION@/$(PACKAGE_VERSION)/g' \
	    -e 's/@RELEASE@/$(PACKAGE_RELEASE)/g' \
	< chroma-manager.spec.in > chroma-manager.spec
	# workaround setuptools
	touch .chroma-manager.wsgi
	python setup.py sdist
	rm -f .chroma-manager.wsgi

rpms: cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/chroma-manager-$(PACKAGE_VERSION).tar.gz _topdir/SOURCES
	cp chroma-storage-init.sh chroma-worker-init.sh chroma-host-discover-init.sh chroma-manager.conf logrotate.cfg _topdir/SOURCES
	cp chroma-manager.spec _topdir/SPECS
	rpmbuild -bb --define "_topdir $$(pwd)/_topdir" _topdir/SPECS/chroma-manager.spec
	mv _topdir/RPMS/noarch/chroma-manager-*$(PACKAGE_VERSION)-$(PACKAGE_RELEASE).noarch.rpm dist/
	rm -rf _topdir

docs: version
	virtualenv myenv
	cd myenv; \
	. bin/activate; \
	pip install -r ../requirements.txt; \
	cd ../docs; \
	make SPHINXBUILD="$$PWD/../myenv/bin/sphinx-build"

.PHONY: docs
