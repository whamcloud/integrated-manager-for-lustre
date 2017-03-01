include ../include/Makefile.distro

SRC_REPO = http://dl.fedoraproject.org/pub/epel/$(EL_MAJOR)/x86_64/

ifeq ($(EL_MAJOR), 7)
INITIAL_IN_TREE := true
ALL_RPMS       := libuv-1.10.2-1.el7.x86_64.rpm
NO_REQUIREMENT := libuv
else ifeq ($(EL_MAJOR), 6)
ALL_RPMS       := 
else
$(error "Unknown major el version $(EL_MAJOR)")
endif

include ../include/Makefile.fetch-from-repo
