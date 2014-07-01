TOP ?= $(shell while [[ $$PWD != */chroma-dependencies ]]; do cd ..; done; echo $$PWD)
include $(TOP)/include/Makefile.meta
REPO = $(TOP)/repo/

SUBDIRS ?= $(shell find . -mindepth 2 -maxdepth 2 -name Makefile | sed  -e '/.*\.old/d' -e 's/^\.\/\([^/]*\)\/.*$$/\1/')

all: repo

.PHONY: rpms clean distclean install requirements
rpms clean distclean install requirements:: $(SUBDIRS)

rpms: TARGET=rpms
clean: TARGET=clean
distclean: TARGET=distclean
install: TARGET=install
requirements: TARGET=requirements

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

$(SUBDIRS): cleanrepo force
	$(MAKE) TOP=$(TOP) REPO=$(REPO) -C $@ $(TARGET)

cleanrepo:
	if [ $(TARGET) = install ]; then \
		rm -rf $(REPO);          \
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
