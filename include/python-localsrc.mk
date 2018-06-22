include include/git-versioning.mk

ifeq ($(strip $(VERSION)),)
VERSION         := $(shell set -x; PYTHONPATH=$(MODULE_SUBDIR) python -c \
		     "import scm_version; print scm_version.VERSION")
endif

ifeq ($(strip $(PACKAGE_VERSION)),)
PACKAGE_VERSION := $(shell set -x; PYTHONPATH=$(MODULE_SUBDIR) python -c \
		     "import scm_version; print scm_version.PACKAGE_VERSION")
endif

include include/common.mk
include include/python-common.mk
include include/rpm-common.mk
include include/copr.mk

# should always remove the tarball sources if DIST_VERSION was set
ifneq ($(DIST_VERSION),$(PACKAGE_VERSION))
    $(shell rm -f $(word 1,$(RPM_SOURCES)))
endif

%.egg-info/SOURCES.txt: install_build_deps-stamp
	python setup.py egg_info

deps: $(subst -,_,$(NAME)).egg-info/SOURCES.txt
	sed -e 's/^/dist\/python-$(NAME)-$(PACKAGE_VERSION).tar.gz: /' < $< > deps

dist/$(NAME)-$(PACKAGE_VERSION).tar.gz: Makefile $(MODULE_SUBDIR)/__init__.py
	echo "jenkins_fold:start:Make Agent Tarball"
	rm -f MANIFEST
	python setup.py sdist
	# TODO - is this really necessary?  time precedence
	#        of the tarball vs. the product in _topdir/
	#        should simply require that any older product
	#        in _topdir/ will just be rebuilt
	# if we made a new tarball, get rid of all previous
	# build product
	rm -rf _topdir
	echo "jenkins_fold:end:Make Agent Tarball"

dist: dist/$(NAME)-$(PACKAGE_VERSION).tar.gz

ifneq ($(DIST_VERSION),$(PACKAGE_VERSION))
$(RPM_SOURCES): # why do we want this prereq? dist/$(NAME)-$(PACKAGE_VERSION).tar.gz
# this builds the RPM from the Source(s) specified in
# the specfile.  i don't think this is what we want here.
# here, we want to build an rpm from the source tree
# let's see what time tells us we want to do
	if ! spectool $(RPM_DIST_VERSION_ARG)                  \
		   -g $(RPM_SPEC); then                        \
	    echo "Failed to fetch $@.";                        \
	    echo "Is this an unpublished version still?";      \
	    echo "Perhaps you want to assign a PR branch name" \
	         "to DIST_VERSION in your make";               \
	    echo "command?";                                   \
	    exit 1;                                            \
	fi
	# uncomment this to build the tarball from the local source tree
	#git archive --prefix $(NAME)-$(DIST_VERSION)/ \
	#            -o $(DIST_VERSION).tar.gz HEAD
else
_topdir/SOURCES/$(NAME)-$(PACKAGE_VERSION).tar.gz: \
	dist/$(NAME)-$(PACKAGE_VERSION).tar.gz
	mkdir -p _topdir/SOURCES
	cp dist/$(NAME)-$(PACKAGE_VERSION).tar.gz _topdir/SOURCES
endif

_topdir/SOURCES/%: %
	mkdir -p _topdir/SOURCES
	cp $< $@

install_build_deps: install_build_deps-stamp

install_build_deps-stamp:
	if ! rpm -q python-setuptools; then   \
	    yum -y install python-setuptools; \
	fi
	touch $@

include deps

tags: deps
	ctags --python-kinds=-i -R --exclude=_topdir
