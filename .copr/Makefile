BUILDROOT:=$(shell [ -d "/build" ] && echo "/build" || echo ".")
TMPDIR:=$(shell mktemp -d)

srpm:
	mkdir -p ${TMPDIR}/_topdir/SOURCES
	mkdir -p ${TMPDIR}/_topdir/SPECS
	mkdir -p ${TMPDIR}/release/rust-iml
	rm -rf ${BUILDROOT}/_topdir
	cargo build --release
	cp target/release/iml-{action-runner,agent,agent-comms,agent-daemon,stratagem} \
		iml-agent-comms.service \
		iml-stratagem.service \
		iml-action-runner.service \
		iml-agent/systemd-units/* \
		${TMPDIR}/release/rust-iml
	tar -czvf ${TMPDIR}/_topdir/SOURCES/rust-iml.tar.gz -C ${TMPDIR}/release/rust-iml .
	cp rust-iml.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/rust-iml.spec
	cp -rf ${TMPDIR}/_topdir ${BUILDROOT}/
	cp -f _topdir/SRPMS/*.rpm $(outdir)
