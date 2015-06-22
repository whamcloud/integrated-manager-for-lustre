RPMS			:= lustre-client lustre-client-source
DESC			:= Lustre Client for SLES12
override REPO		:= $(dir $(patsubst %/,%,$(REPO)))/repo-lustre-client-sles12
VERSION			:= $(shell rpm --qf '%{version}' -qp $(REPO)/lustre-client-[0-9]*.rpm)

include ../include/Makefile.bundle
