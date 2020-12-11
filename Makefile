NAME          := iml-manager
MODULE_SUBDIR  = chroma_manager
DEVELOP_DEPS  := version
DEVELOP_POST  := ./manage.py dev_setup
DIST_DEPS     := version $(COPR_REPO_TARGETS)
RPM_OPTS = -D "_topdir $(CURDIR)/_topdir"
ifdef RPM_DIST
	RPM_OPTS += -D "dist ${RPM_DIST}"
endif

# SET MFL_COPR_REPO in .copr/Makefile
TAGS_ARGS      := --exclude=chroma-manager/_topdir     \
	          --exclude=chroma-\*/myenv\*              \
	          --exclude=chroma_test_env                \
	          --exclude=chroma-manager/chroma_test_env \
	          --exclude=chroma_unit_test_env           \
	          --exclude=workspace

# Always nuke the DB when running tests?
ALWAYS_NUKE_DB ?= false

# Always nuke logs when running tests?
ALWAYS_NUKE_LOGS ?= false

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

all: copr-rpms rpms device-scanner-rpms iml-gui-rpm docker-rpms

local:
	$(MAKE) RPM_DIST="0.$(shell date '+%s')" all

check:
	black --check ./
	cargo fmt --all -- --check
	cargo check --locked --all-targets
	cargo clippy -- -W warnings
	cargo check --locked --manifest-path iml-system-rpm-tests/Cargo.toml --tests
	cargo clippy --manifest-path iml-system-rpm-tests/Cargo.toml --tests -- -W warnings
	cargo check --locked --manifest-path iml-system-docker-tests/Cargo.toml --tests
	cargo clippy --manifest-path iml-system-docker-tests/Cargo.toml --tests -- -W warnings

fmt:
	black ./
	cargo fmt --all
	cargo fmt --all --manifest-path iml-system-rpm-tests/Cargo.toml
	cargo fmt --all --manifest-path iml-system-docker-tests/Cargo.toml

iml-gui-rpm:
	$(MAKE) -f .copr/Makefile iml-gui-srpm outdir=.
	rpmbuild --rebuild ${RPM_OPTS} _topdir/SRPMS/rust-iml-gui-*.src.rpm

rpms:
	$(MAKE) -f .copr/Makefile iml-srpm outdir=.
	rpmbuild --rebuild ${RPM_OPTS} _topdir/SRPMS/python-iml-manager-*.src.rpm

copr-rpms:
	$(MAKE) -f .copr/Makefile srpm outdir=.
	rpmbuild --rebuild ${RPM_OPTS} _topdir/SRPMS/rust-iml-*.src.rpm

docker-rpms:
	$(MAKE) -C docker save
	$(MAKE) -f .copr/Makefile iml-docker-srpm outdir=.
	rpmbuild --rebuild ${RPM_OPTS} _topdir/SRPMS/iml-docker-*.src.rpm

device-scanner-rpms:
	$(MAKE) -f .copr/Makefile device-scanner-srpm outdir=.
	rpmbuild --rebuild ${RPM_OPTS} _topdir/SRPMS/iml-device-scanner-*.src.rpm

cleandist:
	rm -rf dist
	mkdir dist

extraclean: clean
	cargo clean
	find . -name \*~ -delete

clean:
	rm -rf _topdir /tmp/tmp.* *.src.rpm

nuke_db:
	echo "Wiping $(DB_NAME) DB..."; \
	dropdb $(DB_NAME); \
	createdb -O $(DB_USER) $(DB_NAME)

migrate_db:
	psql chroma -c "CREATE EXTENSION IF NOT EXISTS btree_gist;"
	@./manage.py migrate
	cargo sqlx migrate run

localrepo:
	cd _topdir/RPMS; createrepo .

nuke_logs:
	@$(ALWAYS_NUKE_LOGS) && { \
		echo "Scrubbing devel logs..."; \
		rm -f $(CURDIR)/*{.,_}log; \
	} || true

dev_setup: nuke_db nuke_logs
	@./manage.py dev_setup || exit $$?

service_tests: dev_setup
	@echo "Running service tests..."
	@PYTHONPATH=. nosetests $(NOSE_ARGS) tests/services 2>&1 | tee test-services.log; \
	exit $${PIPESTATUS[0]}

unit_tests unit-tests:
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

tests test: unit_tests feature_tests integration_tests service_tests

install_requirements: requirements.txt
	echo "jenkins_fold:start:Install Python requirements"
	pip install --upgrade pip;                              \
	pip install --upgrade setuptools;                       \
	pip install -Ur requirements.txt
	echo "jenkins_fold:end:Install Python requirements"

download: install_requirements

substs:
	$(MAKE) -f .copr/Makefile substs outdir=.

clean_substs:
	if [ -n "$(SUBSTS)" ]; then \
	    rm -f $(SUBSTS);        \
	fi

chroma_test_env: chroma_test_env/bin/activate

chroma_test_env/bin/activate: chroma-manager/requirements.txt
	test -d chroma_test_env || virtualenv --no-site-packages chroma_test_env
	chroma_test_env/bin/pip install -r chroma-manager/requirements.txt
	touch chroma_test_env/bin/activate

.PHONY: download substs
