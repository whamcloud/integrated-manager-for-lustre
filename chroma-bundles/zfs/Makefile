include ../../chroma-dependencies/include/Makefile.distro
include ../../chroma-dependencies/include/Makefile.zfs_version-$(DISTRO)

override REPO		:= $(dir $(patsubst %/,%,$(REPO)))/repo-lustre
RPMS			:= zfs spl zfs-dkms dkms libuutil1 libnvpair1 libzfs2 libzpool2
EXCLUDES		:=
DESC			:= ZFS
VERSION			:= $(shell rpm --qf '%{version}' -qp $(REPO)/zfs-[0-9]*.x86_64.rpm)
RELEASE			:= $(shell rpm --qf '%{release}' -qp $(REPO)/zfs-[0-9]*.x86_64.rpm)
OTHER			:=

include ../include/Makefile.bundle

# target for debugging variable assignments and macros from commandline
print-%: ; @$(error $* is $($*) ($(value $*)) (from $(origin $*)))
