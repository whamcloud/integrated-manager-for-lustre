RPMS			:= lustre
BUNDLE_PACKAGES := lustre lustre-modules
EXCLUDES		:= e2fsprogs e2fsprogs-libs
DESC			:= Lustre
RPM_VERSION		:= $(shell rpm --qf '%{version}' -qp $(REPO)/lustre-[0-9]*.rpm)
NAME			:= $(notdir $(CURDIR))-$(RPM_VERSION)

include ../include/Makefile.bundle
