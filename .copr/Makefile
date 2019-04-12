BUILDROOT:=$(shell [ -d "/build" ] && echo "/build" || echo ".")
TMPDIR:=$(shell mktemp -d)

srpm:
	mkdir -p ${TMPDIR}/_topdir/SOURCES
	mkdir -p ${TMPDIR}/_topdir/SPECS
	mkdir -p ${TMPDIR}/release/rust-iml
	rm -rf ${BUILDROOT}/_topdir
	if ! rpm -q lustre-client 2> /dev/null; then \
		cp lustre-client.repo /etc/yum.repos.d/; \
		yum -y -q install lustre-client;\
	fi
	cargo build --release
	cp target/release/iml-{action-runner,agent,agent-comms,agent-daemon,stratagem,warp-drive} \
		iml-agent-comms.service \
		iml-stratagem.service \
		iml-action-runner.service \
		iml-action-runner.socket \
		iml-agent/systemd-units/* \
		iml-warp-drive/systemd-units/* \
		${TMPDIR}/release/rust-iml
	tar -czvf ${TMPDIR}/_topdir/SOURCES/rust-iml.tar.gz -C ${TMPDIR}/release/rust-iml .
	cp rust-iml.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/rust-iml.spec
	cp -rf ${TMPDIR}/_topdir ${BUILDROOT}/
	cp -f _topdir/SRPMS/*.rpm $(outdir)
