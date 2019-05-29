NAME          := iml-manager
MODULE_SUBDIR  = chroma_manager
DEVELOP_DEPS  := version
DEVELOP_POST  := ./manage.py dev_setup
DIST_DEPS     := version $(COPR_REPO_TARGETS)

MFL_COPR_REPO=managerforlustre/manager-for-lustre-devel
MFL_REPO_OWNER := $(firstword $(subst /, ,$(MFL_COPR_REPO)))
MFL_REPO_NAME  := $(word 2,$(subst /, ,$(MFL_COPR_REPO)))
MFL_COPR_NAME  := $(MFL_REPO_OWNER)-$(MFL_REPO_NAME)

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

COPR_REPO_TARGETS := tests/framework/utils/defaults.sh tests/framework/chroma_support.repo tests/framework/services/runner.sh base.repo chroma_support.repo tests/framework/integration/shared_storage_configuration/full_cluster/cluster_setup

SUBSTS := $(COPR_REPO_TARGETS)

all: copr-rpms rpms

rpms:
	$(MAKE) -f .copr/Makefile iml-srpm outdir=.
	rpmbuild -D "_topdir $(CURDIR)/_topdir" -bb _topdir/SPECS/python-iml-manager.spec

copr-rpms:
	$(MAKE) -f .copr/Makefile srpm outdir=.
	rpmbuild -D "_topdir $(pwd)/_topdir" -bb _topdir/SPECS/rust-iml.spec

cleandist:
	rm -rf dist
	mkdir dist

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
	@./manage.py dev_setup || exit $$?

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

base.repo: base.repo.in Makefile

chroma_support.repo: tests/framework/chroma_support.repo.in Makefile

tests/framework/chroma_support.repo: tests/framework/chroma_support.repo.in Makefile

tests/framework/utils/defaults.sh: tests/framework/utils/defaults.sh.in Makefile

tests/framework/services/runner.sh: tests/framework/services/runner.sh.in Makefile

tests/framework/integration/shared_storage_configuration/full_cluster/cluster_setup: tests/framework/integration/shared_storage_configuration/full_cluster/cluster_setup.in Makefile

$(COPR_REPO_TARGETS):
	sed -e 's/@MFL_COPR_REPO@/$(subst /,\/,$(MFL_COPR_REPO))/g' \
	    -e 's/@MFL_COPR_NAME@/$(MFL_COPR_NAME)/g'               \
	    -e 's/@MFL_REPO_OWNER@/$(MFL_REPO_OWNER)/g'             \
	    -e 's/@MFL_REPO_NAME@/$(MFL_REPO_NAME)/g' < $< > $@

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
	time vagrant destroy -f
	if [ -f ~/.ssh/config ]; then                                   \
	    sed -ie '/# VAGRANT START/,/# VAGRANT END/d' ~/.ssh/config; \
	fi;                                                             \
	if [ -f  ~/.ssh/authorized_keys ]; then                         \
	    sed -ie '/IML Vagrant cluster/d' ~/.ssh/authorized_keys;    \
	fi
	if rpm -q vagrant-libvirt ||                                         \
	   rpm -q sclo-vagrant1-vagrant-libvirt; then                        \
	    export LIBVIRT_DEFAULT_URI=qemu:///system;                       \
	    for net in integrated-manager-for-lustre{0,1,2,3} vagrant-libvirt; do \
	        virsh net-destroy $$net || true;                             \
	        virsh net-undefine $$net || true;                            \
	    done;                                                            \
	fi

create_cluster:
	set -e;                         \
	if [ ! -d ~/.ssh ]; then        \
	    mkdir -p ~/.ssh;            \
	    chmod 700 ~/.ssh;           \
	fi
	set -e;                                              \
	if [ -f ~/ssh-vagrant-site-keys ]; then              \
	    cp ~/ssh-vagrant-site-keys site-authorized_keys; \
	fi
	time vagrant up
	HOSTNAME=$${HOSTNAME:-$$(hostname)};                                      \
	domainname="$${HOSTNAME#*.}";                                             \
	hostname="$${HOSTNAME%%.*}";                                              \
	(echo "# VAGRANT START";                                                  \
	 vagrant ssh-config |                                                     \
	 sed -e "/^Host/s/\(vm.*\)/\1 $$hostname\1 $$hostname\1.$$domainname /g; s/^  User vagrant/  User root/g"; \
	 echo "# VAGRANT END") >> ~/.ssh/config
	# need to have the ssh key that the VMs will use to reach back
	# for virsh commands in .ssh/authorized_keys
	set -e;                                               \
	if [ ! -f ~/.ssh/authorized_keys ]; then              \
	    touch ~/.ssh/authorized_keys;                     \
	    chmod 600  ~/.ssh/authorized_keys;                \
	fi;                                                   \
	if ! grep -qf id_rsa.pub ~/.ssh/authorized_keys; then \
	    (echo -n "command=\"$$PWD/vagrant-virsh\" ";      \
	     cat id_rsa.pub) >> ~/.ssh/authorized_keys;       \
	fi
	if rpm -q vagrant-libvirt ||                                                     \
	   rpm -q sclo-vagrant1-vagrant-libvirt; then                                    \
	    set -e;                                                                      \
	    if $${JENKINS:-false}; then                                                  \
	        HOSTNAME=$${HOSTNAME:-$$(hostname)};                                     \
	        vm_prefix="$${HOSTNAME%%.*}";                                            \
	    fi;                                                                          \
	    export LIBVIRT_DEFAULT_URI=qemu:///system;                                   \
	    if ! virsh list --all | grep -q $${vm_prefix}vm; then                        \
	        exit 0;                                                                  \
	    fi;                                                                          \
	    EDITOR=./edit_network virsh net-edit vagrant-libvirt;                        \
	    virsh net-destroy vagrant-libvirt;                                           \
	    virsh net-start vagrant-libvirt;                                             \
	    stopped_nodes="";                                                            \
	    for node in {2..9}; do                                                       \
	        stopped_nodes+="$$node";                                                 \
	        virsh shutdown $${vm_prefix}vm$$node;                                    \
	    done;                                                                        \
	    for node in {5..8}; do                                                       \
	        if ! virsh dumpxml $${vm_prefix}vm$$node |                               \
	          grep "<controller type='scsi' index='0' model='virtio-scsi'>"; then    \
	            EDITOR=./edit_scsi virsh edit $${vm_prefix}vm$$node;                 \
	            echo "Modified vm$$node to use virtio-scsi";                         \
	        else                                                                     \
	            echo "Interesting.  vm$$node already has virtio-scsi support in it"; \
	        fi;                                                                      \
	    done;                                                                        \
	    started_nodes="";                                                            \
	    while [ -n "$$stopped_nodes" ]; do                                           \
	        for node in {2..9}; do                                                   \
	            if [[ $$stopped_nodes = *$$node* ]] &&                               \
	              ! virsh list | grep -q $${vm_prefix}vm$$node; then                 \
	                virsh start $${vm_prefix}vm$$node;                               \
	                stopped_nodes=$${stopped_nodes/$$node/};                         \
	                started_nodes+="$$node";                                         \
	            fi;                                                                  \
	        done;                                                                    \
	        sleep 1;                                                                 \
	    done;                                                                        \
	    while [ -n "$$started_nodes" ]; do                                           \
	        for node in {2..9}; do                                                   \
	            if [[ $$started_nodes = *$$node* ]] &&                               \
	               ssh vm$$node hostname; then                                       \
	                started_nodes=$${started_nodes/$$node/};                         \
	                if [ -f ~/.ssh/id_rsa.pub ]; then                                \
	                    ssh -i id_rsa root@vm$$node "cat >> .ssh/authorized_keys"    \
	                       < ~/.ssh/id_rsa.pub;                                      \
	                fi;                                                              \
	            fi;                                                                  \
	        done;                                                                    \
	        sleep 1;                                                                 \
	    done;                                                                        \
	fi

reset_cluster: destroy_cluster create_cluster

install_production: reset_cluster
	bash -x scripts/install_dev_cluster

# To run a specific test:
# make TESTS=tests/integration/shared_storage_configuration/test_example_api_client.py:TestExampleApiClient.test_login ssi_tests
# set NOSE_ARGS="-x" to stop on the first failure
ssi_tests: tests/framework/utils/defaults.sh chroma-bundles/chroma_support.repo.in
	tests/framework/integration/shared_storage_configuration/full_cluster/jenkins_steps/main $@

upgrade_tests: tests/framework/utils/defaults.sh chroma-bundles/chroma_support.repo.in
	tests/framework/integration/installation_and_upgrade/jenkins_steps/main $@

efs_tests: tests/framework/utils/defaults.sh chroma-bundles/chroma_support.repo.in
	tests/framework/integration/existing_filesystem_configuration/jenkins_steps/main $@

chroma_test_env: chroma_test_env/bin/activate

chroma_test_env/bin/activate: chroma-manager/requirements.txt
	test -d chroma_test_env || virtualenv --no-site-packages chroma_test_env
	chroma_test_env/bin/pip install -r chroma-manager/requirements.txt
	touch chroma_test_env/bin/activate

.PHONY: download substs
