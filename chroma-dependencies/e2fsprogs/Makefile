include ../include/Makefile.e2fsprogs_version

E2FSPROGS_RELEASE := $(E2FSPROGS_VERSION)-$(E2FSPROGS_RHEL_RELEASE)

SRC_REPO = $(URL)/$(E2FSPROGS_VERSION)/el6/RPMS/x86_64/

ALL_RPMS = e2fsprogs-$(E2FSPROGS_RELEASE).el6.x86_64.rpm e2fsprogs-devel-$(E2FSPROGS_RELEASE).el6.x86_64.rpm e2fsprogs-libs-$(E2FSPROGS_RELEASE).el6.x86_64.rpm libcom_err-$(E2FSPROGS_RELEASE).el6.x86_64.rpm libcom_err-devel-$(E2FSPROGS_RELEASE).el6.x86_64.rpm libss-$(E2FSPROGS_RELEASE).el6.x86_64.rpm libss-devel-$(E2FSPROGS_RELEASE).el6.x86_64.rpm
NO_REQUIREMENT = e2fsprogs e2fsprogs-devel e2fsprogs-libs libcom_err libcom_err-devel libss libss-devel

include ../include/Makefile.fetch-from-repo
