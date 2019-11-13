BUILDROOT:=$(shell [ -d "/build" ] && echo "/build" || echo ".")
TMPDIR:=$(shell mktemp -d)

srpm:
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}
	mkdir -p ${TMPDIR}/package
	rm -rf ${BUILDROOT}/_topdir
	cargo build --target wasm32-unknown-unknown --release
	wasm-bindgen target/wasm32-unknown-unknown/release/package.wasm \
		--target no-modules \
		--out-dir ${TMPDIR}/package \
		--out-name package
	tar cvf ${TMPDIR}/_topdir/SOURCES/iml-wasm-components.tar -C ${TMPDIR}/package .
	cp iml-wasm-components.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/iml-wasm-components.spec
	cp -rf ${TMPDIR}/_topdir ${BUILDROOT}/
	cp -f ${TMPDIR}/_topdir/SRPMS/*.rpm $(outdir)

.PHONY: srpm