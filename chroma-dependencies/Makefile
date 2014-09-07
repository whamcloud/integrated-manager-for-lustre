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
	# these are the ones provided by EL
	echo "https://dl.dropboxusercontent.com/s/0hk2e06aeujotx0/netaddr-0.7.5.zip"
	echo "paramiko==1.7.5"
	echo "pycrypto==2.0.1"
	echo "psycopg2==2.0.14"
	echo "simplejson==2.0.9"
	sed -e '/^#/d' < ../chroma-manager/requirements.dev
	# can't pip install the right versions for these dependencies:
	# echo "python>=2.6.5"

$(SUBDIRS): do_cleanrepo force
	$(MAKE) TOP=$(TOP) REPO=$(REPO) -C $@ $(TARGET)

do_cleanrepo:
	if [ $(TARGET) = install ]; then \
		make cleanrepo;          \
		mkdir $(REPO);           \
	fi

.PHONY: force
force :;

repo: install
	for dir in repo*; do           \
		pushd $$dir;           \
		createrepo --pretty .; \
		popd;                  \
	done

FORCE:

docs:
	@echo "Nothing to do here"
