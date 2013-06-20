include ../include/Makefile.version

# Override this if you don't want to use detected bundles
USE_DETECTED_BUNDLES ?= true
DEV_SETUP_BUNDLES ?= $(shell $(USE_DETECTED_BUNDLES) && { ls $(CURDIR)/repo/*.profile >/dev/null 2>&1 || echo "--no-bundles"; } || echo "--no-bundles")

# Always nuke the DB when running tests?
ALWAYS_NUKE_DB ?= false

# Always nuke logs when running tests?
ALWAYS_NUKE_LOGS ?= false

# Location of cluster configs
SIM_CLUSTER_CONFIG ?= $(CURDIR)/tests/simulator.json
FCI_CLUSTER_CONFIG ?= $(CURDIR)/tests/full_cluster.json

# Misc test config
DB_NAME ?= chroma
DB_USER ?= $(DB_NAME)
TEST_HTTPD_PORT ?= 8000

# Test runner options
BEHAVE_ARGS ?= -q --stop
NOSE_ARGS ?= --verbose

all: rpms docs

cleandist:
	rm -rf  dist
	mkdir dist

version:
	echo 'VERSION = "$(VERSION)"' > scm_version.py
	echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"' >> scm_version.py
	echo 'BUILD = "$(BUILD_NUMBER)"' >> scm_version.py
	echo 'IS_RELEASE = $(IS_RELEASE)' >> scm_version.py

develop: version
	$(MAKE) -C ../chroma-agent develop
	$(MAKE) -C ../cluster-sim develop
	python setup.py develop
	./manage.py dev_setup $(DEV_SETUP_BUNDLES)

nuke_db:
	@$(ALWAYS_NUKE_DB) && { \
		echo "Wiping $(DB_NAME) DB..."; \
		dropdb $(DB_NAME); \
		createdb -O $(DB_USER) $(DB_NAME); \
	} || true

nuke_logs:
	@$(ALWAYS_NUKE_LOGS) && { \
		echo "Scrubbing devel logs..."; \
		rm -f $(CURDIR)/*.log; \
	} || true

dev_setup: nuke_db nuke_logs
	@./manage.py dev_setup $(DEV_SETUP_BUNDLES) || exit $$?

supervisor: dev_setup
	@./manage.py supervisor || exit $$?

running_supervisor:
	@nc -w1 -d localhost $(TEST_HTTPD_PORT) || { \
		echo "You need to run 'make supervisor' in another terminal, then restart the tests."; \
		exit 1; \
	}

$(FCI_CLUSTER_CONFIG):
	@echo "In order to run these tests, you must create $(FCI_CLUSTER_CONFIG) yourself."
	@exit 1

fci full_cluster_integration: $(FCI_CLUSTER_CONFIG) running_supervisor
	@echo "Running integration tests against a full cluster ..."
	@$(CURDIR)/tests/integration/run_tests -c $(FCI_CLUSTER_CONFIG) \
		$(CURDIR)/tests/integration/shared_storage_configuration \
		2>&1 | tee fci-integration.log; \
	exit $${PIPESTATUS[0]}

integration_tests: running_supervisor
	@echo "Running integration tests against the simulator..."
	$(CURDIR)/tests/integration/run_tests -c $(SIM_CLUSTER_CONFIG) \
		$(CURDIR)/tests/integration/shared_storage_configuration \
		2>&1 | tee sim-integration.log; \
	exit $${PIPESTATUS[0]}

service_tests: dev_setup
	@echo "Running service tests..."
	@nosetests $(NOSE_ARGS) tests/services 2>&1 | tee test-services.log; \
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

tests test: unit_tests agent_tests feature_tests service_tests integration_tests

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
