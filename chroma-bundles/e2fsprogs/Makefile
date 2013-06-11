RPMS		:= e2fsprogs e2fsprogs-libs
DESC		:= e2fs utilities
RPM_VERSION := $(shell rpm --qf '%{version}' -qp $(REPO)/e2fsprogs-[0-9]*.rpm)
NAME		:= $(notdir $(CURDIR))-$(RPM_VERSION)

include ../include/Makefile.bundle
