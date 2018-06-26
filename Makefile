NAME          := iml-manager
#SUBPACKAGES   := management
#TEST_DEPS     := python2-tablib python2-iml-common1.4 python-netaddr \
#                 python2-toolz python-django
MODULE_SUBDIR  = chroma_manager
DEVELOP_DEPS  := version
DEVELOP_POST  := ./manage.py dev_setup $(DEV_SETUP_BUNDLES)
DIST_DEPS     := storage_server.repo version $(COPR_REPO_TARGETS)

MFL_COPR_REPO=managerforlustre/manager-for-lustre-devel
MFL_REPO_OWNER := $(firstword $(subst /, ,$(MFL_COPR_REPO)))
MFL_REPO_NAME  := $(word 2,$(subst /, ,$(MFL_COPR_REPO)))

TAGS_ARGS      := --exclude=chroma-manager/_topdir     \
	          --exclude=chroma-\*/myenv\*              \
	          --exclude=chroma_test_env                \
	          --exclude=chroma-manager/chroma_test_env \
	          --exclude=chroma_unit_test_env           \
	          --exclude=workspace


#include ../include/Makefile.version
include include/python-localsrc.mk

ARCH := $(shell echo $$(uname -m))

# Fixup proxies if needed
PREFIXED_PROXIES := if [ -n "$(HTTP_PROXY)" ] && [[ "$(HTTP_PROXY)" != "http://"* ]]; then \
	export HTTP_PROXY=http://$(HTTP_PROXY); \
	export http_proxy=http://$(HTTP_PROXY); \
	export HTTPS_PROXY=http://$(HTTPS_PROXY); \
	export https_proxy=http://$(HTTPS_PROXY); \
fi;

# Override this if you don't want to use detected bundles
USE_DETECTED_BUNDLES ?= true
DEV_SETUP_BUNDLES ?= $(shell $(USE_DETECTED_BUNDLES) && { ls $(CURDIR)/repo/*.profile >/dev/null 2>&1 || echo "--no-bundles"; } || echo "--no-bundles")

# Always nuke the DB when running tests?
ALWAYS_NUKE_DB ?= false

# Always nuke logs when running tests?
ALWAYS_NUKE_LOGS ?= false

# Location of cluster config
FCI_CLUSTER_CONFIG ?= $(CURDIR)/tests/full_cluster.json

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

MFL_REPO_OWNER := $(firstword $(subst /, ,$(MFL_COPR_REPO)))
MFL_REPO_NAME := $(word 2,$(subst /, ,$(MFL_COPR_REPO)))

COPR_REPO_TARGETS := storage_server.repo tests/framework/utils/defaults.sh chroma_support.repo

SUBSTS := $(COPR_REPO_TARGETS)

all: rpms

cleandist:
	rm -rf  dist
	mkdir dist

version:
	echo 'VERSION = "$(VERSION)"' > scm_version.py
	echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"' >> scm_version.py
	echo 'BUILD = "$(BUILD_NUMBER)"' >> scm_version.py
	echo 'IS_RELEASE = $(IS_RELEASE)' >> scm_version.py

nuke_db:
	@$(ALWAYS_NUKE_DB) && { \
		echo "Wiping $(DB_NAME) DB..."; \
		dropdb $(DB_NAME); \
		createdb -O $(DB_USER) $(DB_NAME); \
	} || true

nuke_logs:
	@$(ALWAYS_NUKE_LOGS) && { \
		echo "Scrubbing devel logs..."; \
		rm -f $(CURDIR)/*{.,_}log; \
	} || true

dev_setup: nuke_db nuke_logs
	@./manage.py dev_setup $(DEV_SETUP_BUNDLES) || exit $$?

$(FCI_CLUSTER_CONFIG):
	@echo "In order to run these tests, you must create $(FCI_CLUSTER_CONFIG) yourself."
	@exit 1

fci full_cluster_integration: $(FCI_CLUSTER_CONFIG)
	@echo "Running integration tests against a full cluster ..."
	@$(CURDIR)/tests/integration/run_tests -c $(FCI_CLUSTER_CONFIG) \
		$(CURDIR)/tests/integration/shared_storage_configuration \
		2>&1 | tee fci-integration.log; \
	exit $${PIPESTATUS[0]}

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

storage_server.repo: storage_server.repo.in Makefile

chroma_support.repo: chroma_support.repo.in Makefile

tests/framework/utils/defaults.sh: tests/framework/utils/defaults.sh.in Makefile

$(COPR_REPO_TARGETS):
	sed -e 's/@MFL_COPR_REPO@/$(subst /,\/,$(MFL_COPR_REPO))/g' \
	    -e 's/@MFL_REPO_OWNER@/$(MFL_REPO_OWNER)/g'             \
	    -e 's/@MFL_REPO_NAME@/$(MFL_REPO_NAME)/g' < $< > $@

#rpms: cleandist tarball
#	echo "jenkins_fold:start:Make Manager RPMS"
#	rm -rf _topdir
#	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/$(ARCH)}
#	cp dist/chroma-manager-$(PACKAGE_VERSION).tar.gz _topdir/SOURCES
#	gzip -c chroma-config.1 > chroma-config.1.gz
#	cp iml-corosync.service iml-gunicorn.service iml-http-agent.service iml-job-scheduler.service _topdir/SOURCES
#	cp iml-lustre-audit.service iml-manager.target iml-plugin-runner.service iml-power-control.service _topdir/SOURCES
#	cp iml-settings-populator.service iml-stats.service iml-syslog.service _topdir/SOURCES
#	cp chroma-host-discover-init.sh logrotate.cfg chroma-config.1.gz _topdir/SOURCES
#	cp chroma-manager.spec _topdir/SPECS
#	set -e;                                                \
#	dist=$$(rpm --eval %dist);                             \
#	dist=$${dist/.centos/};                                \
#	rpmbuild --define "_topdir $$(pwd)/_topdir"            \
#		 --define "version $(PACKAGE_VERSION)"         \
#		 --define "package_release $(PACKAGE_RELEASE)" \
#		 --define "%dist $$dist"                       \
#		 -bb _topdir/SPECS/chroma-manager.spec
#	mv _topdir/RPMS/$(ARCH)/chroma-manager-*$(PACKAGE_VERSION)-$(PACKAGE_RELEASE)$$(rpm --eval %{dist} | sed -e 's/\(\.el[0-9][0-9]*\)\.centos/\1/').$(ARCH).rpm dist/
#	rm -rf _topdir
#	echo "jenkins_fold:end:Make Manager RPMS"

install_requirements: requirements.txt
	echo "jenkins_fold:start:Install Python requirements"
	pip install --upgrade pip;                              \
	pip install --upgrade setuptools;                       \
	pip install -Ur requirements.txt
	echo "jenkins_fold:end:Install Python requirements"

download: install_requirements

substs: $(SUBSTS)

clean_substs:
	if [ -n "$(SUBSTS)" ]; then \
	    rm -f $(SUBSTS);        \
	fi

destroy_cluster: Vagrantfile
	vagrant destroy -f
	sed -ie '/# VAGRANT START/,/# VAGRANT END/d' ~/.ssh/config
	sed -ie '/IML Vagrant cluster/d' ~/.ssh/authorized_keys
	export LIBVIRT_DEFAULT_URI=qemu:///system;                       \
	for net in intel-manager-for-lustre{0,1,2,3} vagrant-libvirt; do \
	    virsh net-destroy $$net || true;                             \
	    virsh net-undefine $$net || true;                            \
	done

create_cluster:
	vagrant up
	(echo "# VAGRANT START"; vagrant ssh-config; echo "# VAGRANT END") >> ~/.ssh/config
	# need to have the ssh key that the VMs will use to reach back
	# for virsh commands in .ssh/authorized_keys
	set -e;                                               \
	if ! grep -qf id_rsa.pub ~/.ssh/authorized_keys; then \
	    (echo -n "command=\"$$PWD/vagrant-virsh\" ";      \
	     cat id_rsa.pub) >> ~/.ssh/authorized_keys;       \
	fi
	set -e;                                                                   \
	export LIBVIRT_DEFAULT_URI=qemu:///system;                                \
	if ! virsh list --all | grep -q intel-manager-for-lustre_vm; then         \
	    exit 0;                                                               \
	fi;                                                                       \
	EDITOR=./edit_network virsh net-edit vagrant-libvirt;                     \
	virsh net-destroy vagrant-libvirt;                                        \
	virsh net-start vagrant-libvirt;                                          \
	stopped_nodes="";                                                         \
	for node in {2..9}; do                                                    \
	    stopped_nodes+="$$node";                                              \
	    virsh shutdown intel-manager-for-lustre_vm$$node;                     \
	done;                                                                     \
	for node in {5..8}; do                                                    \
	    if !  virsh dumpxml intel-manager-for-lustre_vm$$node |               \
	      grep "<controller type='scsi' index='0' model='virtio-scsi'>"; then \
	        EDITOR=./edit_scsi virsh edit intel-manager-for-lustre_vm$$node;  \
	        echo "Modified $$vm to use virtio-scsi";                          \
	    else                                                                  \
	        echo "Interesting.  $$vm already has virtio-scsi support in it";  \
	    fi;                                                                   \
	done;                                                                     \
	started_nodes="";                                                         \
	while [ -n "$$stopped_nodes" ]; do                                        \
	    for node in {2..9}; do                                                \
	        if [[ $$stopped_nodes = *$$node* ]] &&                            \
	          ! virsh list | grep -q intel-manager-for-lustre_vm$$node; then  \
	            virsh start intel-manager-for-lustre_vm$$node;                \
	            stopped_nodes=$${stopped_nodes/$$node/};                      \
	            started_nodes+="$$node";                                      \
	        fi;                                                               \
	    done;                                                                 \
	    sleep 1;                                                              \
	done;                                                                     \
	while [ -n "$$started_nodes" ]; do                                        \
	    for node in {2..9}; do                                                \
	        if [[ $$started_nodes = *$$node* ]] &&                            \
	          ssh vm$$node hostname; then                                     \
	            started_nodes=$${started_nodes/$$node/};                      \
	        fi;                                                               \
	    done;                                                                 \
	    sleep 1;                                                              \
	done

reset_cluster: destroy_cluster create_cluster

install_production: reset_cluster
	bash -x scripts/install_dev_cluster

tests/framework/utils/defaults.sh chroma-bundles/chroma_support.repo.in: substs

# To run a specific test:
# make TESTS=tests/integration/shared_storage_configuration/test_example_api_client.py:TestExampleApiClient.test_login ssi_tests
# set NOSE_ARGS="-x" to stop on the first failure
ssi_tests: tests/framework/utils/defaults.sh chroma-bundles/chroma_support.repo.in
	CHROMA_DIR=$$PWD tests/framework/integration/shared_storage_configuration/full_cluster/jenkins_steps/main $@

upgrade_tests:
	tests/framework/integration/installation_and_upgrade/jenkins_steps/main $@

efs_tests:
	pdsh -R ssh -l root -S -w vm[5-9] "echo \"options lnet networks=\\\"tcp(eth1)\\\"\" > /etc/modprobe.d/iml_lnet_module_parameters.conf; systemctl disable firewalld; systemctl stop firewalld"
	tests/framework/integration/existing_filesystem_configuration/jenkins_steps/main $@

chroma_test_env: chroma_test_env/bin/activate

chroma_test_env/bin/activate: chroma-manager/requirements.txt
	test -d chroma_test_env || virtualenv --no-site-packages chroma_test_env
	chroma_test_env/bin/pip install -r chroma-manager/requirements.txt
	touch chroma_test_env/bin/activate

unit_tests: chroma_test_env
	sh -c '. chroma_test_env/bin/activate; make -C chroma-manager unit_tests'

.PHONY: download substs
