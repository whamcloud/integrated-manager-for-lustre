E2FSPROGS_RELEASE = 1.42.9.wc1-0suse
SRC_REPO = http://downloads.whamcloud.com/public/e2fsprogs/1.42.9.wc1/sles11sp3/RPMS/x86_64/

override REPO		:= $(dir $(patsubst %/,%,$(REPO)))/repo-sles-e2fsprogs
ALL_RPMS = e2fsprogs-$(E2FSPROGS_RELEASE).x86_64.rpm e2fsprogs-devel-$(E2FSPROGS_RELEASE).x86_64.rpm libcom_err2-$(E2FSPROGS_RELEASE).x86_64.rpm libcom_err-devel-$(E2FSPROGS_RELEASE).x86_64.rpm libext2fs2-$(E2FSPROGS_RELEASE).x86_64.rpm libext2fs-devel-$(E2FSPROGS_RELEASE).x86_64.rpm
NO_REQUIREMENT = e2fsprogs e2fsprogs-devel libcom_err2 libcom_err-devel libext2fs2 libext2fs-devel

include ../include/Makefile.fetch-from-repo
