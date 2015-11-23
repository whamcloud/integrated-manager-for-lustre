EL_MAJOR = $(shell rpm --eval '%{?rhel}')

SRC_REPO = http://nginx.org/packages/centos/$(EL_MAJOR)/x86_64/RPMS/

ALL_RPMS = nginx-1.8.0-1.el$(EL_MAJOR).ngx.x86_64.rpm
NO_REQUIREMENT = nginx

rpm_file:
	@echo $(ALL_RPMS)

include ../include/Makefile.fetch-from-repo
