TOP ?= $(shell while [[ $$PWD != */chroma-dependencies ]]; do cd ..; done; echo $$PWD)
include $(TOP)/include/Makefile.meta
REPO = $(TOP)/repo/

SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

all: repo

.PHONY: cleanrepo rpms clean distclean install requirements download debug
cleanrepo debug download rpms clean distclean install requirements:: $(SUBDIRS)

rpms: TARGET=rpms
clean: TARGET=clean
distclean: TARGET=distclean
install: TARGET=install
requirements: TARGET=requirements
download: TARGET=download
debug: TARGET=debug
cleanrepo: TARGET=cleanrepo

requirements::
	# these are the ones provided by EL and EPEL
	set -e;                                                   \
	{ echo "../chroma-externals/netaddr-0.7.5.zip";           \
	if [ $(shell rpm --eval '%{?rhel}') -lt 7 ]; then         \
	    echo "paramiko==1.7.5";                               \
	    echo "pycrypto==2.0.1";                               \
	    echo "python-daemon==1.5.2";                          \
	else                                                      \
	    echo "paramiko==1.16.1";                              \
	    echo "pycrypto==2.6.1";                               \
	    echo "python-daemon==1.6 ";                           \
	fi;                                                       \
	echo "amqp==1.4.5";                                       \
	echo "kombu==3.0.19";                                     \
	echo "mimeparse==0.1.3";                                  \
	echo "networkx==1.7";                                     \
	echo "prettytable==0.6";                                  \
	echo "anyjson==0.3.3";                                    \
	echo "lockfile==0.9.1";                                   \
	echo "meld3==0.6.10";                                     \
	echo "ordereddict==1.1";                                  \
	echo "psycopg2==2.0.14";                                  \
	sed -e '/^#/d' < ../chroma-manager/requirements.dev; } >> \
	    $(TOP)/../chroma-manager/requirements.tmp

$(SUBDIRS): do_cleanrepo force
	$(MAKE) TOP=$(TOP) REPO=$(REPO) -C $@ $(TARGET)

do_cleanrepo:
	set -e;                          \
	if [ $(TARGET) = install ]; then \
		make cleanrepo;          \
		mkdir $(REPO);           \
	fi

.PHONY: force
force :;

repo: install
	set -e;                        \
	for dir in repo*; do           \
		pushd $$dir;           \
		createrepo --pretty .; \
		popd;                  \
	done

FORCE:

docs:
	@echo "Nothing to do here"
