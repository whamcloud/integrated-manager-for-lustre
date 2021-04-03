# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.

override SHELL = bash
override .SHELLFLAGS = -eux -o pipefail -c

RPM_OPTS = -D "_topdir $(CURDIR)/_topdir"
ifdef RPM_DIST
	RPM_OPTS += -D "dist ${RPM_DIST}"
endif

TMPDIR:=$(shell mktemp -d)
TARGET:=$(or $(CARGO_TARGET_DIR),target)

# Always nuke the DB when running tests?
ALWAYS_NUKE_DB ?= false

# Always nuke logs when running tests?
ALWAYS_NUKE_LOGS ?= false

# Misc test config
DB_NAME ?= emf
DB_USER ?= $(DB_NAME)

# all: rust-core-rpms device-scanner-rpms emf-gui-rpm sos-rpm
all: rust-core-rpms device-scanner-rpms sos-rpm

tests/framework/utils/defaults.sh: tests/framework/utils/defaults.sh.in Makefile

tests/framework/services/runner.sh: tests/framework/services/runner.sh.in Makefile

rpm-repo-docker:
	docker run --mount type=volume,src=sccache,dst=/.cache/sccache --mount type=volume,src=rust-core-registry,dst=/root/.cargo/registry -v '${CURDIR}:/build:rw' emfteam/emf-centos7-deps make all

rust-core-rpms-docker-local:
	docker run --mount type=volume,src=sccache,dst=/.cache/sccache --mount type=volume,src=cargo_target,dst=/cargo_target --mount type=volume,src=rust-core-registry,dst=/root/.cargo/registry --env CARGO_TARGET_DIR=/cargo_target  -v '${CURDIR}:/build:delegated' emfteam/emf-centos7-deps make rust-core-rpms-local

local:
	$(MAKE) RPM_DIST="0.$(shell date '+%s')" all

check:
	black --check ./
	cargo fmt --all -- --check
	cargo check --locked --all-targets
	cargo clippy -- -W warnings
	cargo check --locked --manifest-path emf-system-rpm-tests/Cargo.toml --tests
	cargo clippy --manifest-path emf-system-rpm-tests/Cargo.toml --tests -- -W warnings
	cargo check --locked --manifest-path emf-gui/crate/Cargo.toml --tests
	cargo clippy --manifest-path emf-gui/crate/Cargo.toml --tests -- -W warnings

fmt:
	black ./
	cargo fmt --all
	cargo fmt --all --manifest-path emf-system-rpm-tests/Cargo.toml
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
	cp -r ${TARGET}/release/emf-{agent,api,corosync,device,host,journal,mailbox,network,network-ib,ntp,ostpool,report,sfa,snapshot,state-machine,stats,task-runner,warp-drive,timer,action-agent,device-agent,corosync-agent,host-agent,journal-agent,network-agent,network-ib-agent,ntp-agent,ostpool-agent,postoffice-agent,snapshot-agent,stats-agent} \
		emf-api.service \
		emf-mailbox.service \
		emf-report.conf \
		emf-report.service \
		emf-sfa.service \
		emf-task-runner.service \
		emf-timer.service \
		emf-state-machine/systemd-units/* \
		emf-warp-drive/systemd-units/* \
		emf-services/systemd-units/* \
		emf-manager-redirect.conf \
		emf-manager.target \
		bootstrap.conf \
		embedded.conf \
		nginx/ \
		postgres/ \
		influx/ \
		${TMPDIR}/release/rust-core
	cp emf-agent/tmpfiles.conf ${TMPDIR}/release/rust-core
	cp ${TARGET}/release/emf ${TMPDIR}/release/rust-core
	cp ${TARGET}/release/emf-config ${TMPDIR}/release/rust-core
	cp -rf grafana ${TMPDIR}/release/rust-core
	cp -rf nginx ${TMPDIR}/release/rust-core
	cp -rf kuma ${TMPDIR}/release/rust-core

	mkdir -p ${TMPDIR}/release/rust-core/emf-agent-units
	cp -rf emf-agent/systemd-units ${TMPDIR}/release/rust-core/emf-agent-units
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}
	tar -czvf ${TMPDIR}/_topdir/SOURCES/rust-core.tar.gz -C ${TMPDIR}/release/rust-core .
	cp rust-emf.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bb ${RPM_OPTS} -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/rust-emf.spec
	rm -rf ${TMPDIR}/_topdir/SOURCES/*
	cp -rf ${TMPDIR}/_topdir .
	rm -rf ${TMPDIR}

rust-core-rpms-local:
	$(MAKE) RPM_DIST="0.$(shell date '+%s')" rust-core-rpms

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
	psql $(DB_USER) -c "CREATE EXTENSION IF NOT EXISTS btree_gist;"
	cargo sqlx migrate run

sqlx-data.json:
	CARGO_TARGET_DIR=/tmp/sqlx_target cargo sqlx prepare --merged -- --tests

nuke_logs:
	@$(ALWAYS_NUKE_LOGS) && { \
		echo "Scrubbing devel logs..."; \
		rm -f $(CURDIR)/*{.,_}log; \
	} || true

