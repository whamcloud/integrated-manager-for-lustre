CARGO_HOME ?= $(HOME)/.cargo
export PATH := $(PATH):$(CARGO_HOME)/bin

BUILDROOT:=$(shell [ -d "/build" ] && echo "/build" || echo ".")
TMPDIR:=$(shell mktemp -d)


srpm:
	yum remove -y cargo
	mkdir -p ${TMPDIR}/_topdir/SOURCES
	mkdir -p ${TMPDIR}/_topdir/SPECS
	mkdir -p ${TMPDIR}/package
	rm -rf ${BUILDROOT}/_topdir
	curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable
	rustup default stable
	rustup target add wasm32-unknown-unknown
	cargo build --target wasm32-unknown-unknown --release
	cargo install wasm-bindgen-cli
	wasm-bindgen target/wasm32-unknown-unknown/release/iml_action_dropdown.wasm --target no-modules --out-dir ${TMPDIR}/package --out-name package
	tar cvf ${TMPDIR}/_topdir/SOURCES/iml-wasm-components.tar -C ${TMPDIR}/package .
	cp iml-wasm-components.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/iml-wasm-components.spec
	cp -rf ${TMPDIR}/_topdir ${BUILDROOT}/
	cp -f _topdir/SRPMS/*.rpm $(outdir)

.PHONY: srpm