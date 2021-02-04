NAME          := emf-manager
MODULE_SUBDIR  = chroma_manager
DEVELOP_DEPS  := version
DEVELOP_POST  := ./manage.py dev_setup
DIST_DEPS     := version $(COPR_REPO_TARGETS)
RPM_OPTS = -D "_topdir $(CURDIR)/_topdir"
ifdef RPM_DIST
	RPM_OPTS += -D "dist ${RPM_DIST}"
endif

TMPDIR:=$(shell mktemp -d)
TARGET:=$(or $(CARGO_TARGET_DIR),target)

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

# Test runner options
NOSE_ARGS ?= --stop

all: rust-core-rpms device-scanner-rpms emf-gui-rpm docker-rpms

MFL_COPR_REPO=managerforlustre/manager-for-lustre-devel
MFL_REPO_OWNER := $(firstword $(subst /, ,$(MFL_COPR_REPO)))
MFL_REPO_NAME  := $(word 2,$(subst /, ,$(MFL_COPR_REPO)))
MFL_COPR_NAME  := $(MFL_REPO_OWNER)-$(MFL_REPO_NAME)

# Files needing substitutions for MFL_COPR/REPO_*
SUBSTS_SHELL := tests/framework/services/runner.sh
SUBSTS_REPOS := base.repo chroma_support.repo tests/framework/chroma_support.repo

SUBSTS := $(SUBSTS_SHELL) $(SUBSTS_REPOS)

base.repo: base.repo.in Makefile

chroma_support.repo: tests/framework/chroma_support.repo.in Makefile

tests/framework/chroma_support.repo: tests/framework/chroma_support.repo.in Makefile

tests/framework/utils/defaults.sh: tests/framework/utils/defaults.sh.in Makefile

tests/framework/services/runner.sh: tests/framework/services/runner.sh.in Makefile

$(SUBSTS):
	sed -e 's/@MFL_COPR_REPO@/$(subst /,\/,$(MFL_COPR_REPO))/g' \
	    -e 's/@MFL_COPR_NAME@/$(MFL_COPR_NAME)/g'               \
	    -e 's/@MFL_REPO_OWNER@/$(MFL_REPO_OWNER)/g'             \
	    -e 's/@MFL_REPO_NAME@/$(MFL_REPO_NAME)/g' < $< > $@

substs: $(SUBSTS)
	chmod +x $(SUBSTS_SHELL)

base.repo: base.repo.in Makefile

rpm-repo-docker:
	docker run --mount type=volume,src=sccache,dst=/.cache/sccache --mount type=volume,src=rust-core-registry,dst=/root/.cargo/registry -v '${CURDIR}:/build:rw' emfteam/emf-centos7-deps make all

local:
	$(MAKE) RPM_DIST="0.$(shell date '+%s')" all

check:
	black --check ./
	cargo fmt --all -- --check
	cargo check --locked --all-targets
	cargo clippy -- -W warnings
	cargo check --locked --manifest-path emf-system-rpm-tests/Cargo.toml --tests
	cargo clippy --manifest-path emf-system-rpm-tests/Cargo.toml --tests -- -W warnings
	cargo check --locked --manifest-path emf-system-docker-tests/Cargo.toml --tests
	cargo clippy --manifest-path emf-system-docker-tests/Cargo.toml --tests -- -W warnings
	cargo check --locked --manifest-path emf-gui/crate/Cargo.toml --tests
	cargo clippy --manifest-path emf-gui/crate/Cargo.toml --tests -- -W warnings

fmt:
	black ./
	cargo fmt --all
	cargo fmt --all --manifest-path emf-system-rpm-tests/Cargo.toml
	cargo fmt --all --manifest-path emf-system-docker-tests/Cargo.toml
	cargo fmt --all --manifest-path emf-gui/crate/Cargo.toml

.PHONY: deb deb-repo
deb deb-repo:
	make -f Makefile.deb $@

emf-gui-rpm:
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}

	cd emf-gui; \
	yarn install; \
	yarn build:release
	tar cvf ${TMPDIR}/_topdir/SOURCES/emf-gui.tar -C ./emf-gui dist

	cp emf-gui/rust-emf-gui.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bb ${RPM_OPTS} -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/rust-emf-gui.spec

	rm -rf ${TMPDIR}/_topdir/SOURCES/*
	cp -rf ${TMPDIR}/_topdir .
	rm -rf ${TMPDIR}

sos-rpm:
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}
	cd emf-sos-plugin; \
	python setup.py sdist --formats bztar -d ${TMPDIR}/_topdir/SOURCES/
	cp emf-sos-plugin/emf-sos-plugin.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bb ${RPM_OPTS} -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/emf-sos-plugin.spec
	rm -rf ${TMPDIR}/_topdir/{SOURCES,BUILD,SPECS}/*
	cp -rf ${TMPDIR}/_topdir .
	rm -rf ${TMPDIR}

rust-core-rpms:
	mkdir -p ${TMPDIR}/release/rust-core
	cargo build --release
	cp ${TARGET}/release/emf-{action-runner,agent,agent-comms,agent-daemon,api,corosync,device,journal,mailbox,network,ntp,ostpool,postoffice,report,sfa,snapshot,stats,task-runner,warp-drive,timer} \
		emf-action-runner.service \
		emf-action-runner.socket \
		emf-agent-comms.service \
		emf-agent/systemd-units/* \
		emf-api.service \
		emf-device.service \
		emf-journal.service \
		emf-mailbox.service \
		emf-network.service \
		emf-ntp.service \
		emf-ostpool.service \
		emf-postoffice.service \
		emf-report.conf \
		emf-report.service \
		emf-rust-corosync.service \
		emf-rust-stats.service \
		emf-sfa.service \
		emf-snapshot.service \
		emf-task-runner.service \
		emf-timer.service \
		emf-warp-drive/systemd-units/* \
		${TMPDIR}/release/rust-core
	cp ${TARGET}/release/emf ${TMPDIR}/release/rust-core
	cp ${TARGET}/release/emf-config ${TMPDIR}/release/rust-core
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}
	tar -czvf ${TMPDIR}/_topdir/SOURCES/rust-core.tar.gz -C ${TMPDIR}/release/rust-core .
	cp rust-emf.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bb ${RPM_OPTS} -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/rust-emf.spec
	rm -rf ${TMPDIR}/_topdir/SOURCES/*
	cp -rf ${TMPDIR}/_topdir .
	rm -rf ${TMPDIR}

docker-rpms:
	$(MAKE) -C docker save
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}
	mkdir -p ${TMPDIR}/scratch/emf-docker

	cp -r docker/{docker-compose.yml,emf-images.tgz,update-embedded.sh,copy-embedded-settings} ${TMPDIR}/scratch/emf-docker/
	cp emf-docker.service ${TMPDIR}/scratch/emf-docker/
	tar -czvf ${TMPDIR}/_topdir/SOURCES/emf-docker.tar.gz -C ${TMPDIR}/scratch/emf-docker .

	cp emf-docker.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bb ${RPM_OPTS} -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/emf-docker.spec

	rm -rf ${TMPDIR}/_topdir/{SOURCES,SPECS}/*
	cp -rf ${TMPDIR}/_topdir .
	rm -rf ${TMPDIR}

device-scanner-rpms:
	mkdir -p ${TMPDIR}/release/emf-device-scanner
	cd device-scanner; \
	cargo build --release; \
	cp {device-scanner-daemon,mount-emitter}/systemd-units/* \
		uevent-listener/udev-rules/* \
		${TARGET}/release/device-scanner-daemon \
		${TARGET}/release/mount-emitter \
		${TARGET}/release/swap-emitter \
		${TARGET}/release/uevent-listener \
		${TMPDIR}/release/emf-device-scanner
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}
	tar -czvf ${TMPDIR}/_topdir/SOURCES/emf-device-scanner.tar.gz -C ${TMPDIR}/release/emf-device-scanner .
	cp device-scanner/emf-device-scanner.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bb ${RPM_OPTS} -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/emf-device-scanner.spec
	rm -rf ${TMPDIR}/_topdir/SOURCES/*
	cp -rf ${TMPDIR}/_topdir .
	rm -rf ${TMPDIR}

extraclean:
	git clean -fdx

clean:
	rm -rf _topdir /tmp/tmp.* /tmp/yarn-* *.src.rpm

cleandist:
	rm -rf dist
	mkdir dist

nuke_db:
	echo "Wiping $(DB_NAME) DB..."; \
	dropdb $(DB_NAME); \
	createdb -O $(DB_USER) $(DB_NAME)

migrate_db:
	psql chroma -c "CREATE EXTENSION IF NOT EXISTS btree_gist;"
	@./manage.py migrate
	cargo sqlx migrate run

sqlx-data.json:
	cargo sqlx prepare --merged -- --tests

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

tests test: unit_tests service_tests

clean_substs:
	if [ -n "$(SUBSTS)" ]; then \
	    rm -f $(SUBSTS);        \
	fi

.PHONY: substs
