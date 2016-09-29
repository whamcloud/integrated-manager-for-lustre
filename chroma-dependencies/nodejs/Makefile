include ../include/Makefile.distro

ifeq ($(EL_MAJOR), 7)
SRC_REPO = https://rpm.nodesource.com/pub_6.x/el/7/x86_64/
ALL_RPMS = nodejs-6.7.0-1nodesource.el7.centos.x86_64.rpm
else
SRC_REPO = https://rpm.nodesource.com/pub_0.10/el/6/x86_64/
ALL_RPMS = nodejs-0.10.47-1nodesource.el6.x86_64.rpm
endif

NO_REQUIREMENT = nodejs

rpm_file:
	@echo $(ALL_RPMS)

include ../include/Makefile.fetch-from-repo
