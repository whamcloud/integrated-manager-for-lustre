RPM_SPEC		?= $(NAME).spec
RPMLINT_REQUIRED	?= true

CLEAN += _topdir
DISTCLEAN += dist

# I would love nothing more than to build the specfile using the
# standard %.in rule but we need it to be made before many of the
# following variable evaluations so we can't leave it to be built
# during target processing.
# So we end up having to run this every time.
$(shell if [ $(RPM_SPEC).in -nt $(RPM_SPEC) ]; then   \
	    sed -e "s/@VERSION@/$(PACKAGE_VERSION)/g" \
	        -e "s/@RELEASE@/$(PACKAGE_RELEASE)/g" \
	        < $(RPM_SPEC).in > $(RPM_SPEC);       \
	fi)

ifndef DIST_VERSION
DIST_VERSION	     := $(PACKAGE_VERSION)
else
RPM_DIST_VERSION_ARG := --define dist_version\ $(DIST_VERSION)
endif

RPM_DIST=$(subst .centos,,$(shell rpm --eval %dist))

# probably a way to determine this from parsespec methods
ALL_PKGS := $(NAME) $(addprefix $(NAME)-,$(SUBPACKAGES))

PACKAGE_VRD   := $(PACKAGE_VERSION)-$(PACKAGE_RELEASE)$(RPM_DIST)

RPM_SOURCES   := $(shell spectool --define version\ $(PACKAGE_VERSION) \
				  $(RPM_DIST_VERSION_ARG)              \
				  --define "epel 1"                    \
				  -l $(RPM_SPEC) |                     \
				  sed -e 's/^[^:]*:  *//' -e 's/.*\///')

COMMON_RPMBUILD_ARGS += $(RPM_DIST_VERSION_ARG)                       \
			--define "version $(PACKAGE_VERSION)"         \
			--define "package_release $(PACKAGE_RELEASE)" \
			--define "epel 1"                             \
			--define "%dist $(RPM_DIST)"

RPMBUILD_ARGS += $(COMMON_RPMBUILD_ARGS) --define "_topdir $$(pwd)/_topdir"

TARGET_SRPM   := _topdir/SRPMS/$(shell rpm $(RPMBUILD_ARGS) -q                       \
				           --qf %{name}-%{version}-%{release}\\n     \
				           --specfile $(RPM_SPEC) | head -1).src.rpm
all: rpms

genfiles: $(RPM_SPEC)

develop:
	python setup.py develop

tarball: dist/$(NAME)-$(PACKAGE_VERSION).tar.gz

%: %.in
	sed -e "s/@VERSION@/$(PACKAGE_VERSION)/g"           \
	    -e "s/@RELEASE@/$(PACKAGE_RELEASE)/g" < $< > $@

_topdir/SPECS/$(RPM_SPEC): $(RPM_SPEC)
	mkdir -p _topdir/SPECS
	cp $< $@

_topdir/SOURCES/%: %
	mkdir -p _topdir/SOURCES
	cp $< $@

srpm: $(TARGET_SRPM)

$(TARGET_SRPM): $(addprefix _topdir/SOURCES/, $(RPM_SOURCES)) \
		_topdir/SPECS/$(RPM_SPEC)
	mkdir -p _topdir/SRPMS
	rpmbuild $(RPMBUILD_ARGS) -bs _topdir/SPECS/$(RPM_SPEC)

rpms: $(TARGET_RPMS)

# see https://stackoverflow.com/questions/2973445/ for why we subst
# the "rpm" for "%" to effectively turn this into a multiple matching
# target pattern rule
$(subst rpm,%,$(TARGET_RPMS)): \
		$(addprefix _topdir/SOURCES/, $(RPM_SOURCES)) \
		_topdir/SPECS/$(RPM_SPEC)
	echo "jenkins_fold:start:Make Agent RPMS"
	rm -rf $(addprefix _topdir/, BUILD RPMS)
	mkdir -p $(addprefix _topdir/, BUILD $(addprefix RPMS/,noarch x86_64))
	rpmbuild $(RPMBUILD_ARGS) -bb _topdir/SPECS/$(RPM_SPEC)
	echo "jenkins_fold:end:Make Agent RPMS"

build_test: $(TARGET_SRPM)
	$${TRAVIS:-false} && echo "travis_fold:start:mock" || true
	mock -v $(COMMON_RPMBUILD_ARGS) $<
	$${TRAVIS:-false} && echo "travis_fold:end:mock" || true

# it's not clear yet that we need/want this
#rpm_deps: $(RPM_SPEC)
#	spectool -l $(RPM_SPEC) | \
#	    sed -e 's/^Source[0-9][0-9]*: \(.*\/\)\(.*\)/\2: ; curl -L -O \1\2/' > $@
#
#include rpm_deps

rpmlint: $(RPM_SPEC)
	if ! rpmlint $<; then                                  \
	    if ! $(RPMLINT_REQUIRED); then                     \
	        echo "rpmlint not required, skipping failure"; \
	    else                                               \
	        exit 1;                                        \
	    fi;                                                \
	fi

.PHONY: rpms srpm test test_dependencies build_test dist develop \
	all genfiles setuphooks rpmlint

include include/githooks.mk

# make a release
tag:
	if [ -z "$(TAG)" ]; then              \
	    echo "Usage: make TAG=<tag> tag"; \
	    exit 1;                           \
	fi
	make genfiles
	if git status --porcelain | grep ^\ M; then       \
	    echo "You have uncommitted diffs that "       \
	         "you need to commit before you can tag"; \
	    exit 1;                                       \
	fi
	git tag $(TAG)
