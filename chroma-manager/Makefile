include ../include/Makefile.version

NPM := $(shell if which npm 2>/dev/null; then true; else echo npm; fi)

ARCH := $(shell echo $$(uname -m))

# Fixup proxies if needed
PREFIXED_PROXIES := if [ -n "$(HTTP_PROXY)" ] && [[ "$(HTTP_PROXY)" != "http://"* ]]; then \
	export HTTP_PROXY=http://$(HTTP_PROXY); \
	export http_proxy=http://$(HTTP_PROXY); \
	export HTTPS_PROXY=http://$(HTTPS_PROXY); \
	export https_proxy=http://$(HTTPS_PROXY); \
fi;

# Override this if you don't want to use detected bundles
USE_DETECTED_BUNDLES ?= true
DEV_SETUP_BUNDLES ?= $(shell $(USE_DETECTED_BUNDLES) && { ls $(CURDIR)/repo/*.profile >/dev/null 2>&1 || echo "--no-bundles"; } || echo "--no-bundles")

# Always nuke the DB when running tests?
ALWAYS_NUKE_DB ?= false

# Always nuke logs when running tests?
ALWAYS_NUKE_LOGS ?= false

# Always wipe the simulated cluster config before starting?
ALWAYS_NUKE_SIM_CFG ?= true

# Location of cluster configs
SIM_CLUSTER_CONFIG ?= $(CURDIR)/tests/simulator.json
FCI_CLUSTER_CONFIG ?= $(CURDIR)/tests/full_cluster.json

# Location of the cluster-sim script
CLUSTER_SIM_BIN := $(shell if which cluster-sim 2>/dev/null; then true; else echo $(word 1,$(subst :, ,$(PATH)))/cluster-sim; fi)
CLUSTER_SIM_CFG ?= $(CURDIR)/cluster_sim
CLUSTER_SIM_SETUP_ARGS ?= --cluster_size 2 --psu_count 2 --worker_count 4
CLUSTER_SIM_REGISTER_ARGS ?= --username $(DEV_USERNAME) --password $(DEV_PASSWORD) --create_pdu_entries

# Misc test config
DB_NAME ?= chroma
DB_USER ?= $(DB_NAME)
TEST_HTTPD_PORT ?= 8000
DEV_USERNAME = admin
DEV_PASSWORD = lustre

# Test runner options
BEHAVE_ARGS ?= -q --stop
NOSE_ARGS ?= --stop

ZIP_TYPE := $(shell if [ "$(ZIP_DEV)" == "true" ]; then echo '-dev'; else echo ''; fi)

all: rpms docs

cleandist:
	rm -rf  dist
	mkdir dist

version:
	echo 'VERSION = "$(VERSION)"' > scm_version.py
	echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"' >> scm_version.py
	echo 'BUILD = "$(BUILD_NUMBER)"' >> scm_version.py
	echo 'IS_RELEASE = $(IS_RELEASE)' >> scm_version.py

develop: version ui-modules
	$(MAKE) -C ../chroma-agent develop
	$(MAKE) -C ../cluster-sim develop
	python setup.py develop
	./manage.py dev_setup $(DEV_SETUP_BUNDLES)

$(NPM):
	@echo "You need to install $@ first... (brew install $@?)"
	@echo "Or maybe you don't even have the which(1) command"
	exit 1

ziplocker: $(NPM)
	@echo "Setting up ziplocker module"; \
	mkdir -p ui-modules/node_modules/@intel-js && \
	cd ui-modules/node_modules/@intel-js && \
	rm -rf ./* && \
	cp -r ../../../../chroma-externals/ui-modules/node_modules/@intel-js/ziplocker ./

ui-modules: ziplocker
	@echo "Setting up ui-modules zipdev: $(ZIP_DEV)"; \
	cd ui-modules && \
	node_modules/@intel-js/ziplocker/bin/zip-install$(ZIP_TYPE) --overrides.ziplockDir='../../chroma-externals/'

gui: ui-modules
	@echo "Building GUI for deployment"; \
	cd ui-modules/node_modules/@intel-js/gui/gulp && \
	npm run build -- --dest-dir='../../../../..'

socket-worker: gui
	@echo "Building socket worker"; \
	cd ui-modules/node_modules/@intel-js/socket-worker && \
	npm run build && \
	mv bundle.js ../../../../chroma_ui/static/chroma_ui && \
	mv bundle.map.json ../../../../chroma_ui/static/chroma_ui

build-ui: socket-worker
	@echo "Building UI Components";

nuke_db:
	@$(ALWAYS_NUKE_DB) && { \
		echo "Wiping $(DB_NAME) DB..."; \
		dropdb $(DB_NAME); \
		createdb -O $(DB_USER) $(DB_NAME); \
	} || true

nuke_logs:
	@$(ALWAYS_NUKE_LOGS) && { \
		echo "Scrubbing devel logs..."; \
		rm -f $(CURDIR)/*{.,_}log; \
	} || true

$(CLUSTER_SIM_BIN):
	$(MAKE) develop

sim simulator: $(CLUSTER_SIM_BIN) running_supervisor
	@if [ -d $(CLUSTER_SIM_CFG) ]; then \
		if $(ALWAYS_NUKE_SIM_CFG); then \
			echo "Nuking old cluster sim cfg..."; \
			rm -fr $(CLUSTER_SIM_CFG); \
			cluster-sim --config $(CLUSTER_SIM_CFG) setup $(CLUSTER_SIM_SETUP_ARGS); \
		fi; \
	else \
			cluster-sim --config $(CLUSTER_SIM_CFG) setup $(CLUSTER_SIM_SETUP_ARGS); \
	fi; \
	cluster-sim --config $(CLUSTER_SIM_CFG) register $(CLUSTER_SIM_REGISTER_ARGS)

dev_setup: nuke_db nuke_logs
	@./manage.py dev_setup $(DEV_SETUP_BUNDLES) || exit $$?

supervisor: dev_setup
	@./manage.py supervisor || exit $$?

running_supervisor:
	@nc -w1 -d localhost $(TEST_HTTPD_PORT) || { \
		echo "You need to run 'make supervisor' in another terminal, then retry this command."; \
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
	NOSE_ARGS=$(NOSE_ARGS) \
	$(CURDIR)/tests/integration/run_tests -c $(SIM_CLUSTER_CONFIG) \
		$(CURDIR)/tests/integration/shared_storage_configuration \
		2>&1 | tee sim-integration.log; \
	exit $${PIPESTATUS[0]}

service_tests: dev_setup
	@while $(MAKE) running_supervisor >/dev/null; do \
		spid=`ps aux | awk '/p[y]thon .\/manage.py supervisor/ {print $$2}'`; \
		kill $$spid; \
		sleep 1; \
	done
	@echo "Running service tests..."
	@PYTHONPATH=. nosetests $(NOSE_ARGS) tests/services 2>&1 | tee test-services.log; \
	exit $${PIPESTATUS[0]}

agent_tests:
	@echo "Running agent tests..."
	@NOSE_ARGS=$(NOSE_ARGS) $(MAKE) -C ../chroma-agent test 2>&1 \
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

tests test: unit_tests agent_tests feature_tests integration_tests service_tests

tarball: version build-ui
	rm -f MANIFEST
	python scripts/production_supervisord.py supervisord.conf > production_supervisord.conf
	# workaround setuptools
	touch .chroma-manager.py
	touch .production_supervisord.conf
	python setup.py sdist
	rm -f .chroma-manager.py
	rm -f .production_supervisord.conf

rpms: cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/$(ARCH)}
	cp dist/chroma-manager-$(PACKAGE_VERSION).tar.gz _topdir/SOURCES
	cp chroma-supervisor-init.sh chroma-host-discover-init.sh production_supervisord.conf logrotate.cfg _topdir/SOURCES
	cp chroma-manager.spec _topdir/SPECS
	rpmbuild --define "_topdir $$(pwd)/_topdir" \
		--define "version $(PACKAGE_VERSION)" \
		--define "package_release $(PACKAGE_RELEASE)" \
		-bb _topdir/SPECS/chroma-manager.spec
	mv _topdir/RPMS/$(ARCH)/chroma-manager-*$(PACKAGE_VERSION)-$(PACKAGE_RELEASE)$$(rpm --eval %{dist}).$(ARCH).rpm dist/
	rm -rf _topdir

requirements:
	rm -f requirements.tmp
	$(MAKE) -C ../chroma-dependencies requirements
	{ echo "# DO NOT UPDATE THIS FILE MANUALLY.";                                         \
	echo "# This file is generated automatically.";                                       \
	echo "# If you want to add a new requirement please see:";                            \
	echo "# http://wiki.whamcloud.com/display/HYD/Adding+and+Updating+IML+Requirements";  \
	echo "# DO NOT UPDATE THIS FILE MANUALLY.  See the warning at the top of this file."; \
	sort < requirements.tmp; } > requirements.txt
	rm -f requirements.tmp
	if grep ^make requirements.txt; then                      \
		echo "why is this not quiet like it should be?";  \
		sed -i -e '/^make\[[0-9]\]: /d' requirements.txt; \
	fi

download: requirements
	pip-python install --download ../chroma-externals -r requirements.txt

docs: requirements version
	set -e ; \
	if [ -z $(VIRTUAL_ENV) ] ; then \
		virtualenv myenv; \
		. myenv/bin/activate; \
		CACHE=$$(pwd)/../chroma-externals; \
		echo "# Using pip cache at $$CACHE"; \
		python tests/utils/pip_install_requirements.py $$CACHE; \
	fi; \
	$(MAKE) -C docs/ && cp docs/dist/*.tar.gz dist/

.PHONY: docs download build-ui socket-worker gui ui-modules ziplocker
