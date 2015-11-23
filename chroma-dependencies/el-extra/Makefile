EL_MAJOR = $(shell rpm --eval '%{?rhel}')

SRC_REPO = http://mirror.centos.org/centos/$(EL_MAJOR)/extras/x86_64/Packages/

ifeq ($(EL_MAJOR), 7)
ALL_RPMS = python-gunicorn-18.0-2.el7.noarch.rpm
else
ALL_RPMS =
endif
include ../include/Makefile.fetch-from-repo
