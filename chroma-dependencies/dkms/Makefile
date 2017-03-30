include ../include/Makefile.distro

SRC_REPO = http://dl.fedoraproject.org/pub/epel/$(EL_MAJOR)/x86_64/

override REPO   := $(dir $(patsubst %/,%,$(REPO)))/repo-lustre

ALL_RPMS        := dkms-2.3-1.20161202gitde1dca9.el$(EL_MAJOR).noarch.rpm

ifeq ($(EL_MAJOR), 7)
INITIAL_IN_TREE := true
endif

NO_REQUIREMENT  := dkms

include ../include/Makefile.fetch-from-repo
