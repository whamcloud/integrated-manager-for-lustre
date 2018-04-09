BUILDER_IS_EL = $(shell rpm --eval '%{?rhel:true}%{!?rhel:false}')

MFL_COPR_REPO=managerforlustre/manager-for-lustre-devel

# Top-level Makefile
SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

.PHONY: all rpms docs subdirs $(SUBDIRS) tags

all: TARGET=all
rpms: TARGET=rpms
docs: TARGET=docs
download: TARGET=download
substs: TARGET=substs
clean_substs: TARGET=clean_substs

all rpms docs download subdirs substs clean_substs: $(SUBDIRS)

cleandist:
	rm -rf dist

dist: cleandist
	mkdir dist

$(SUBDIRS): dist
	set -e; \
	if $(BUILDER_IS_EL); then \
		$(MAKE) MFL_COPR_REPO=$(MFL_COPR_REPO) -C $@ $(TARGET); \
		if [ $(TARGET) != download -a -d $@/dist/ ]; then \
			cp -a $@/dist/* dist/; \
		fi; \
	fi

repo: rpms
	$(MAKE) -C chroma-dependencies repo

bundles: repo
	$(MAKE) MFL_COPR_REPO=$(MFL_COPR_REPO) -C chroma-bundles

deps: repo

tags:
	ctags --python-kinds=-i -R --exclude=chroma-manager/_topdir         \
	                           --exclude=chroma-\*/myenv\*              \
	                           --exclude=chroma_test_env                \
	                           --exclude=chroma-manager/chroma_test_env \
	                           --exclude=chroma-dependencies            \
	                           --exclude=chroma_unit_test_env           \
	                           --exclude=workspace                      \
	                           --exclude=chroma-manager/ui-modules .

# build the chroma-management subdirs before the chroma-dependencies subdir
chroma-dependencies: chroma-manager
chroma-bundles: chroma-dependencies

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
	    for net in intel-manager-for-lustre{0,1,2,3} vagrant-libvirt; do \
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
	 sed -e "/^Host/s/\(vm.*\)/\1 $$hostname\1 $$hostname\1.$$domainname /g"; \
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

chroma-manager/tests/framework/utils/defaults.sh chroma-bundles/chroma_support.repo.in: substs

# To run a specific test:
# make TESTS=tests/integration/shared_storage_configuration/test_example_api_client.py:TestExampleApiClient.test_login ssi_tests
# set NOSE_ARGS="-x" to stop on the first failure
ssi_tests: chroma-manager/tests/framework/utils/defaults.sh chroma-bundles/chroma_support.repo.in
	CHROMA_DIR=$$PWD chroma-manager/tests/framework/integration/shared_storage_configuration/full_cluster/jenkins_steps/main $@

upgrade_tests:
	chroma-manager/tests/framework/integration/installation_and_upgrade/jenkins_steps/main $@

efs_tests:
	pdsh -R ssh -l root -S -w vm[5-9] "echo \"options lnet networks=\\\"tcp(eth1)\\\"\" > /etc/modprobe.d/iml_lnet_module_parameters.conf; systemctl disable firewalld; systemctl stop firewalld"
	chroma-manager/tests/framework/integration/existing_filesystem_configuration/jenkins_steps/main $@

requirements:
	make -C chroma-manager requirements.txt

chroma_test_env: requirements chroma_test_env/bin/activate

chroma_test_env/bin/activate: chroma-manager/requirements.txt
	test -d chroma_test_env || virtualenv --no-site-packages chroma_test_env
	chroma_test_env/bin/pip install -r chroma-manager/requirements.txt
	touch chroma_test_env/bin/activate

unit_tests: chroma_test_env
	sh -c '. chroma_test_env/bin/activate; make -C chroma-manager unit_tests'
