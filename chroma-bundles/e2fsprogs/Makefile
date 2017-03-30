override REPO   := $(dir $(patsubst %/,%,$(REPO)))/repo-lustre
RPMS		:= e2fsprogs e2fsprogs-libs
DESC		:= e2fs utilities
VERSION		:= $(shell rpm --qf '%{version}' -qp $(REPO)/e2fsprogs-[0-9]*.rpm)

include ../include/Makefile.bundle
