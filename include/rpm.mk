RPM_SPEC:= $(NAME).spec

ifneq ($(REPO),)
VERSION := $(shell repoquery --disablerepo=\* --enablerepo=$(REPO) -q --qf "%{version}" $(NAME) | sed -e 's/.el7//g')
RELEASE := $(shell repoquery --disablerepo=\* --enablerepo=$(REPO) -q --qf "%{release}" $(NAME) | sed -e 's/.el7//g')
else
VERSION := $(shell rpmspec -q --srpm --qf "%{version}\n" $(RPM_SPEC))
RELEASE := $(shell rpmspec -q --srpm --qf "%{release}\n" $(RPM_SPEC))
endif

PACKAGE_VERSION ?= $(VERSION)
PACKAGE_RELEASE ?= $(RELEASE).01

TARGET_RPMS = $(NAME)-$(PACKAGE_VERSION)-$(PACKAGE_RELEASE)$(RPM_DIST).noarch.rpm

include include/rpm-common.mk
include include/copr.mk

SRPM            := $(NAME)-$(VERSION)-$(RELEASE).el7.src.rpm

$(SRPM):
	yumdownloader --disablerepo=\* --enablerepo=$(REPO) --source $(NAME)

unpack: $(SRPM)
	rpm2cpio < $(SRPM) | cpio -iu

download: $(SRPM)

$(RPM_SOURCES):
	if ! spectool $(RPM_DIST_VERSION_ARG)                  \
		   --define "epel 1"                           \
		   -g $(RPM_SPEC); then                        \
	    echo "Failed to fetch $@.";                        \
	    exit 1;                                            \
	fi

install_build_deps:
	if [ "$(REPO)" = "epel" ]; then                                                     \
	    if ! rpm -q epel-release; then                                                  \
	        yum -y install                                                              \
	            https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm; \
	    fi;                                                                             \
	else                                                                                \
	    echo "Nothing to do";                                                           \
	fi

.PHONY: unpack download install_build_deps
