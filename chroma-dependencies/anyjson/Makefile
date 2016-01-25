include ../include/Makefile.distro

ifeq ($(EL_MAJOR), 7)
LOCATION := https://dl.fedoraproject.org/pub/epel/7/SRPMS/p/python-anyjson-0.3.3-3.el7.src.rpm
else
LOCATION := https://dl.fedoraproject.org/pub/epel/6/SRPMS/python-anyjson-0.3.3-1.el6.src.rpm
endif

REQUIREMENT := anyjson==0.3.3

include ../include/Makefile.rpm
