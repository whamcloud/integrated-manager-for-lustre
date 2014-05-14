RPMS			:= lustre-client lustre-client-source
DESC			:= Lustre Client for SLES11
override REPO	:= $(dir $(patsubst %/,%,$(REPO)))/repo-sles-client
VERSION			:= $(shell rpm --qf '%{version}' -qp $(REPO)/lustre-client-[0-9]*.rpm)

include ../include/Makefile.bundle
