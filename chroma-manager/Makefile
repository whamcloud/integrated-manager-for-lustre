include ../include/Makefile.version

DEVELOPER_BUNDLES = lustre chroma-agent e2fsprogs

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
	echo 'VERSION = "$(VERSION)"' > scm_version.py
	echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"' >> scm_version.py
	echo 'BUILD = $(BUILD_NUMBER)' >> scm_version.py
	echo 'IS_RELEASE = $(IS_RELEASE)' >> scm_version.py

develop: version
	$(MAKE) -C ../chroma-agent develop
	$(MAKE) -C ../cluster-sim develop
	python setup.py develop
	./manage.py dev_setup --no-bundles

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
	@./manage.py test $(NOSE_ARGS) tests/unit 2>&1 | tee unit.log; \
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
	rpmbuild --define "_topdir $$(pwd)/_topdir" \
		--define "version $(PACKAGE_VERSION)" \
		--define "release $(PACKAGE_RELEASE)" \
		-bb _topdir/SPECS/chroma-manager.spec
	mv _topdir/RPMS/noarch/chroma-manager-*$(PACKAGE_VERSION)-$(PACKAGE_RELEASE).noarch.rpm dist/
	rm -rf _topdir

requirements:
	(echo "# DO NOT UPDATE THIS FILE MANUALLY.";                \
	echo "# This file is generated automatically.";             \
	echo "# If you want to add a new requirement please see:";  \
	echo "# http://wiki.whamcloud.com/display/HYD/Adding+and+Updating+IML+Requirements"; \
	$(MAKE) -s -C ../chroma-dependencies requirements | sort;   \
	echo "# DO NOT UPDATE THIS FILE MANUALLY.  See the warning at the top of this file.")          \
		> requirements.txt
	if grep ^make requirements.txt; then                      \
		echo "why is this not quiet like it should be?";  \
		sed -i -e '/^make\[[0-9]\]: /d' requirements.txt; \
	fi
	
docs: requirements version
	set -e ; \
	if [ -z $(VIRTUAL_ENV) ] ; then \
		virtualenv --system-site-packages myenv ; \
		. myenv/bin/activate; \
		pip install -r ./requirements.txt; \
	fi ; \
	$(MAKE) -C docs/ && cp docs/dist/*.tar.gz dist/

.PHONY: docs
