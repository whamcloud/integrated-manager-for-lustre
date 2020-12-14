BUILDROOT:=$(shell [ -d "/build" ] && echo "/build" || echo ".")
TMPDIR:=$(shell mktemp -d)
TARGET:=$(or $(CARGO_TARGET_DIR),target)

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

tests/framework/integration/shared_storage_configuration/full_cluster/cluster_setup: tests/framework/integration/shared_storage_configuration/full_cluster/cluster_setup.in Makefile

$(SUBSTS):
	sed -e 's/@MFL_COPR_REPO@/$(subst /,\/,$(MFL_COPR_REPO))/g' \
	    -e 's/@MFL_COPR_NAME@/$(MFL_COPR_NAME)/g'               \
	    -e 's/@MFL_REPO_OWNER@/$(MFL_REPO_OWNER)/g'             \
	    -e 's/@MFL_REPO_NAME@/$(MFL_REPO_NAME)/g' < $< > $@

substs: $(SUBSTS)
	chmod +x $(SUBSTS_SHELL)

srpm:
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}
	mkdir -p ${TMPDIR}/release/rust-iml
	cargo build --release
	cp ${TARGET}/release/iml-{action-runner,agent,agent-comms,agent-daemon,api,corosync,device,journal,mailbox,network,ntp,ostpool,postoffice,report,sfa,snapshot,stats,task-runner,warp-drive,timer} \
		iml-action-runner.service \
		iml-action-runner.socket \
		iml-agent-comms.service \
		iml-agent/systemd-units/* \
		iml-api.service \
		iml-device.service \
		iml-journal.service \
		iml-mailbox.service \
		iml-network.service \
		iml-ntp.service \
		iml-ostpool.service \
		iml-postoffice.service \
		iml-report.conf \
		iml-report.service \
		iml-rust-corosync.service \
		iml-rust-stats.service \
		iml-sfa.service \
		iml-snapshot.service \
		iml-task-runner.service \
		iml-timer.service \
		iml-warp-drive/systemd-units/* \
		${TMPDIR}/release/rust-iml
	cp ${TARGET}/release/iml ${TMPDIR}/release/rust-iml
	cp ${TARGET}/release/iml-config ${TMPDIR}/release/rust-iml
	tar -czvf ${TMPDIR}/_topdir/SOURCES/rust-iml.tar.gz -C ${TMPDIR}/release/rust-iml .
	cp rust-iml.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/rust-iml.spec
	cp -rf ${TMPDIR}/_topdir ${BUILDROOT}/
	cp -f ${TMPDIR}/_topdir/SRPMS/*.rpm $(outdir)

iml-docker-srpm:
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}
	mkdir -p ${TMPDIR}/scratch/iml-docker

	cp -r docker/{docker-compose.yml,iml-images.tgz,update-embedded.sh,copy-embedded-settings} ${TMPDIR}/scratch/iml-docker/
	cp iml-docker.service ${TMPDIR}/scratch/iml-docker/
	tar -czvf ${TMPDIR}/_topdir/SOURCES/iml-docker.tar.gz -C ${TMPDIR}/scratch/iml-docker .

	cp iml-docker.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/iml-docker.spec

	cp -rf ${TMPDIR}/_topdir ${BUILDROOT}/
	cp -f ${TMPDIR}/_topdir/SRPMS/*.rpm $(outdir)

iml-deps:
	if ! rpm -q python-devel python-setuptools ed 2> /dev/null; then \
		yum copr enable -y managerforlustre/buildtools; \
		yum install -y python2-devel python2-setuptools ed; \
		yum copr disable -y managerforlustre/buildtools; \
	fi

iml-srpm: iml-deps substs
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}
	mkdir -p ${TMPDIR}/{scratch,configuration}

	cp -r ./{chroma_*,chroma-*,__init__.py,manage.py,scm_version.py,setup.py,settings.py,urls.py,wsgi.py,agent-bootstrap-script.template,*.profile} ${TMPDIR}/scratch
	cp -r ./{*.repo,README.*,licenses,polymorphic,scripts,example_storage_plugin_package,tests,MANIFEST.in} ${TMPDIR}/scratch

	cp ./python-iml-manager.spec ${TMPDIR}/_topdir/SPECS

	cp -r ./grafana ${TMPDIR}/configuration
	cp -r ./nginx ${TMPDIR}/configuration
	cp ./iml-*.service \
		./rabbitmq-env.conf \
		./rabbitmq-server-dropin.conf \
		./iml-manager-redirect.conf \
		./iml-manager.target \
		./chroma-config.1 \
		./logrotate.cfg \
		${TMPDIR}/configuration

	tar -czvf ${TMPDIR}/_topdir/SOURCES/configuration.tar.gz -C ${TMPDIR}/configuration .

	cd ${TMPDIR}/scratch; \
	python setup.py sdist -d ${TMPDIR}/_topdir/SOURCES/

	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/python-iml-manager.spec

	cp -rf ${TMPDIR}/_topdir ${BUILDROOT}/
	cp -r ${TMPDIR}/_topdir/SRPMS/* $(outdir)
	rm -rf ${TMPDIR}

iml-common-srpm:
	yum install -y python2-devel
	mkdir -p ${TMPDIR}/_topdir/SOURCES
	mkdir -p ${TMPDIR}/scratch
	cp -r iml-common/* ${TMPDIR}/scratch

	cd ${TMPDIR}/scratch; \
	python setup.py sdist -d ${TMPDIR}/_topdir/SOURCES/

	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/scratch/python-iml-common.spec
	cp -r ${TMPDIR}/_topdir/SRPMS/* $(outdir)
	rm -rf ${TMPDIR}

python-iml-agent-srpm:
	mkdir -p ${TMPDIR}/_topdir/SOURCES
	mkdir -p ${TMPDIR}/scratch
	cp -r python-iml-agent/* ${TMPDIR}/scratch
	cd ${TMPDIR}/scratch; \
	python setup.py sdist -d ${TMPDIR}/_topdir/SOURCES/

	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/scratch/python-iml-agent.spec
	cp -rf ${TMPDIR}/_topdir ${BUILDROOT}/
	cp -r ${TMPDIR}/_topdir/SRPMS/* $(outdir)
	rm -rf ${TMPDIR}

iml-gui-srpm:
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}

	curl --silent --location https://dl.yarnpkg.com/rpm/yarn.repo | tee /etc/yum.repos.d/yarn.repo
	curl --silent --location https://rpm.nodesource.com/setup_12.x | bash -
	yum install -y yarn

	cd iml-gui; \
	yarn install; \
	yarn build:release
	tar cvf ${TMPDIR}/_topdir/SOURCES/iml-gui.tar -C ./iml-gui dist

	cp iml-gui/rust-iml-gui.spec ${TMPDIR}/_topdir/SPECS/
	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/rust-iml-gui.spec

	cp -rf ${TMPDIR}/_topdir ${BUILDROOT}/
	cp -f ${TMPDIR}/_topdir/SRPMS/*.rpm $(outdir)

device-scanner-srpm:
	mkdir -p ${TMPDIR}/_topdir/{SOURCES,SPECS}
	mkdir -p ${TMPDIR}/release/iml-device-scanner

	cd device-scanner; \
	cargo build --release; \
	cp {device-scanner-daemon,mount-emitter,zed-enhancer}/systemd-units/* \
		{zed-enhancer,uevent-listener}/udev-rules/* \
		${TARGET}/release/device-scanner-daemon \
		${TARGET}/release/{history_event,pool_create,pool_destroy,pool_export,pool_import,vdev_add}-scanner \
		${TARGET}/release/mount-emitter \
		${TARGET}/release/swap-emitter \
		${TARGET}/release/uevent-listener \
		${TARGET}/release/zed-enhancer \
		${TMPDIR}/release/iml-device-scanner


	tar -czvf ${TMPDIR}/_topdir/SOURCES/iml-device-scanner.tar.gz -C ${TMPDIR}/release/iml-device-scanner .
	cp device-scanner/iml-device-scanner.spec ${TMPDIR}/_topdir/SPECS/

	rpmbuild -bs -D "_topdir ${TMPDIR}/_topdir" ${TMPDIR}/_topdir/SPECS/iml-device-scanner.spec

	cp -rf ${TMPDIR}/_topdir ${BUILDROOT}/
	cp -f ${TMPDIR}/_topdir/SRPMS/*.rpm $(outdir)

