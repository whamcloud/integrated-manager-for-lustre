RPMS			:= lustre kernel-ib
EXCLUDES		:= e2fsprogs e2fsprogs-libs
DESC			:= Lustre with the Mellanox OFED
override REPO		:= $(dir $(patsubst %/,%,$(REPO)))/repo-lustre-mellanox
VERSION			:= $(shell rpm --qf '%{version}' -qp $(REPO)/lustre-[0-9]*.rpm)

include ../include/Makefile.bundle
