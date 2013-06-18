RPMS			:= lustre
EXCLUDES		:= e2fsprogs e2fsprogs-libs
DESC			:= Lustre
VERSION			:= $(shell rpm --qf '%{version}' -qp $(REPO)/lustre-[0-9]*.rpm)

include ../include/Makefile.bundle
