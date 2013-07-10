RPMS			:= lustre-client lustre-client-source
EXCLUDES        := e2fsprogs e2fsprogs-libs
DESC			:= Lustre Client
VERSION			:= $(shell rpm --qf '%{version}' -qp $(REPO)/lustre-client-[0-9]*.rpm)

include ../include/Makefile.bundle
