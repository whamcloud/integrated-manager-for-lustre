srpm:
	rm -rf _topdir *.rpm
	rm -rf target/release/rust-iml
	mkdir -p _topdir/SOURCES/
	cargo build --release
	mkdir -p target/release/rust-iml
	cp target/release/iml-{action-runner,agent,agent-daemon,agent-comms,agent-daemon,stratagem} \
		iml-agent-comms.service \
		iml-stratagem.service \
		iml-action-runner.service \
		iml-agent/systemd-units/* \
		target/release/rust-iml
	tar -czvf _topdir/SOURCES/rust-iml.tar.gz -C target/release/rust-iml .
	rpmbuild -bs -D "%_topdir $$PWD/_topdir" rust-iml.spec
	cp -f _topdir/SRPMS/*.rpm $(outdir)
