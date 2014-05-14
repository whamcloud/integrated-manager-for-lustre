RPMS			:= lustre-client-mic lustre-client-mic-source
DESC			:= Lustre Client for Xeon Phi(tm)
override REPO	:= $(dir $(patsubst %/,%,$(REPO)))/repo-xeon-phi-client
VERSION			:= $(shell rpm --qf '%{version}' -qp $(REPO)/lustre-client-mic-[0-9]*.rpm)

include ../include/Makefile.bundle
