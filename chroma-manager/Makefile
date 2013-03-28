
# The build number, for dev/test/support
BUILD := $(shell echo 1.99.0.0.`date -u +%Y%m%d%H%M`.`git rev-parse --short HEAD`)
# The A.B.C.D release number for releases, or a build number for test/dev builds
VERSION := $(BUILD)
# Flag for whether this is a release build
IS_RELEASE := False

ifeq ($(IS_RELEASE),True)
  PACKAGE_VERSION := $(VERSION)
else
  PACKAGE_VERSION := $(BUILD)
endif

PACKAGE_RELEASE := 1

# In development, we want to stop at first failure, but when running
# in a Jenkins job we want all the gory details.
ifdef JENKINS_URL
	BEHAVE_ARGS ?= --junit --junit-directory $$WORKSPACE/test_reports --format plain
	NOSE_ARGS ?= --with-xunit --xunit-file=$WORKSPACE/test_reports/chroma-manager-unit-test-results.xml
else
	BEHAVE_ARGS ?= -q --stop
	NOSE_ARGS ?= --stop
endif

all: rpms docs

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

integration_tests:
	@echo "Running integration tests against the simulator..."
	@nosetests $(NOSE_ARGS) --tc-file=tests/simulator.json --tc-format=json \
		       tests/integration/shared_storage_configuration 2>&1 \
			   | tee integration.log; \
	exit $${PIPESTATUS[0]}

agent_tests:
	@echo "Running agent tests..."
	@$(MAKE) -C ../chroma-agent test $(NOSE_ARGS) 2>&1 \
			| tee ../chroma-agent/unit.log; \
	exit $${PIPESTATUS[0]}

unit_tests:
	@echo "Running standard unit tests..."
	@./manage.py test $(NOSE_ARGS) 2>&1 | tee unit.log; \
	exit $${PIPESTATUS[0]}

feature_tests:
	@echo "Running behave features tests..."
	@for feature in tests/feature/*; do \
		[ -d $$feature ] || continue; \
		logname=feature-$$(basename $$feature); \
		stdout=$$logname.stdout; stderr=$$logname.stderr; \
		behave $(BEHAVE_ARGS) $${feature}/features 2>$$stderr | tee $$stdout; \
		brc=$${PIPESTATUS[0]}; \
		[ $$brc -eq 0 ] || { \
			echo "$$feature failed, logs: $$stdout, $$stderr"; \
	        break; \
		} && true; \
	done; \
	exit $$brc

tests test: unit_tests agent_tests feature_tests integration_tests

tarball: version
	rm -f MANIFEST
	sed -e 's/@VERSION@/$(PACKAGE_VERSION)/g' \
	    -e 's/@RELEASE@/$(PACKAGE_RELEASE)/g' \
	< chroma-manager.spec.in > chroma-manager.spec
	python scripts/production_httpd.py chroma-manager.conf.template > chroma-manager.conf
	python scripts/production_supervisord.py supervisord.conf > production_supervisord.conf
	# workaround setuptools
	touch .chroma-manager.wsgi
	touch .production_supervisord.conf
	python setup.py sdist
	rm -f .chroma-manager.wsgi
	rm -f .production_supervisord.conf

rpms: cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/chroma-manager-$(PACKAGE_VERSION).tar.gz _topdir/SOURCES
	cp chroma-supervisor-init.sh chroma-host-discover-init.sh chroma-manager.conf production_supervisord.conf logrotate.cfg _topdir/SOURCES
	cp chroma-manager.spec _topdir/SPECS
	rpmbuild -bb --define "_topdir $$(pwd)/_topdir" _topdir/SPECS/chroma-manager.spec
	mv _topdir/RPMS/noarch/chroma-manager-*$(PACKAGE_VERSION)-$(PACKAGE_RELEASE).noarch.rpm dist/
	rm -rf _topdir

docs: version
	set -e ; \
	if [ -z $(VIRTUAL_ENV) ] ; then \
		virtualenv myenv ; \
		. myenv/bin/activate; \
		pip install -r ./requirements.txt; \
	fi ; \
	make -C docs/ && cp docs/dist/*.tar.gz dist/

.PHONY: docs
