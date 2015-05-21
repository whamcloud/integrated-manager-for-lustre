DISTRO=el6.6

include ../../chroma-dependencies/include/Makefile.zfs_version-$(DISTRO)

RPMS			:= zfs-dkms dkms
EXCLUDES		:=
DESC			:= ZFS
VERSION			:= $(shell rpm --qf '%{version}' -qp $(REPO)/zfs-[0-9]*.x86_64.rpm)
RELEASE			:= $(shell rpm --qf '%{release}' -qp $(REPO)/zfs-[0-9]*.x86_64.rpm)
OTHER			:= spl-$(VERSION)-$(RELEASE).src.rpm zfs-$(VERSION)-$(RELEASE).src.rpm

include ../include/Makefile.bundle
