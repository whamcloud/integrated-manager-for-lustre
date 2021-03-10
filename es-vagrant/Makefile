override SHELL = bash
override .SHELLFLAGS = -eux -o pipefail -c

VBOX_DIR=$(shell VBoxManage list systemproperties|awk -F ': *' '/^Default machine folder:/{ print $$2 }')
VDISK_DIR=${VBOX_DIR}/esvdisks

help:
	@echo "VBox dir: "${VBOX_DIR}
	@echo "VDisks:   "${VDISK_DIR}

clean:
	rm -rf agent-rpms docker-rpms

destroy: clean
	vagrant destroy --force || true
	find '${VDISK_DIR}' -type f -print -exec VBoxManage closemedium disk {} --delete \;
	rm -rf "${VBOX_DIR}"/node[1-4] "${VBOX_DIR}"/client[1-8] "${VBOX_DIR}"/ubuntu[1-8]

docker-local: docker-rpms
	vagrant rsync || true
	vagrant provision --provision-with=install-docker-rpm

agent-local: agent-rpms
	vagrant rsync || true
	vagrant provision --provision-with=install-agent-rpm

# DIRECTORY BUILD TARGETS
agent-rpms:
	mkdir agent-rpms/
	cp -a ../_topdir/RPMS/noarch/python*-agent*.rpm \
		../_topdir/RPMS/x86_64/rust-*-agent-[0-9]*.rpm \
		../_topdir/RPMS/x86_64/*-device-scanner*.rpm agent-rpms/

docker-rpms:
	mkdir docker-rpms
	cp -a ../_topdir/RPMS/*/*-docker-*.rpm docker-rpms/

