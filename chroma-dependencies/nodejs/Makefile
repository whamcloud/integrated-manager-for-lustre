include ../include/Makefile.distro

ifeq ($(EL_MAJOR), 7)
SRC_REPO = https://rpm.nodesource.com/pub_4.x/el/7/x86_64/
ALL_RPMS = nodejs-4.4.7-1nodesource.el7.centos.x86_64.rpm
else
SRC_REPO = https://rpm.nodesource.com/pub_0.10/el/6/x86_64/
ALL_RPMS = nodejs-0.10.46-1nodesource.el6.x86_64.rpm
endif

NO_REQUIREMENT = nodejs

rpm_file:
	@echo $(ALL_RPMS)

include ../include/Makefile.fetch-from-repo
