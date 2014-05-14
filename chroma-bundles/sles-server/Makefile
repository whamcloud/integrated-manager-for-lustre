RPMS			:= lustre kernel-source kernel-default-devel
DESC			:= Lustre Server for SLES11
override REPO	:= $(dir $(patsubst %/,%,$(REPO)))/repo-sles-server
VERSION			:= $(shell rpm --qf '%{version}' -qp $(REPO)/lustre-[0-9]*.rpm)

include ../include/Makefile.bundle
