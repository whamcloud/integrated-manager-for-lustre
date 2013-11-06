RPMS			:= lustre kernel-headers kernel-devel
EXCLUDES		:= e2fsprogs e2fsprogs-libs
DESC			:= Lustre
override REPO		:= $(dir $(patsubst %/,%,$(REPO)))/repo-lustre
VERSION			:= $(shell rpm --qf '%{version}' -qp $(REPO)/lustre-[0-9]*.rpm)

include ../include/Makefile.bundle
