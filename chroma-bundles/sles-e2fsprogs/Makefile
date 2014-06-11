RPMS		:= e2fsprogs e2fsprogs-devel
DESC		:= e2fs utilities for SLES11
override REPO   := $(dir $(patsubst %/,%,$(REPO)))/repo-sles-e2fsprogs
VERSION		:= $(shell rpm --qf '%{version}' -qp $(REPO)/e2fsprogs-[0-9]*.rpm)

include ../include/Makefile.bundle
