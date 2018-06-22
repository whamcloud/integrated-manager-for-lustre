BUILD_METHOD := PyPI
include include/common.mk
include include/python-common.mk
include include/rpm-common.mk
include include/copr.mk

DISTCLEAN += $(NAME)-*.tar.gz

# don't rebuild if tracked by git since this has to be manually
# updated by a developer because pyp2rpm is just not sufficient
# to produce a working specfile
ifneq ($(shell git ls-files --error-unmatch $(RPM_SPEC) 2>/dev/null),$(RPM_SPEC))
$(RPM_SPEC): include/python-pypi.mk
	#pyp2rpm $(NAME) -t epel7 | sed                  \
	#		      -e '/%check/,/^$$/d' > $@
	pyp2rpm $(NAME) | sed -e 's/python3-/python%{python3_pkgversion}-/' \
			      -e '/%check/,/^$$/d' > $@
endif

$(RPM_SOURCES):
	if ! spectool $(RPM_DIST_VERSION_ARG)                  \
		   --define "epel 1"                           \
		   -g $(RPM_SPEC); then                        \
	    echo "Failed to fetch $@.";                        \
	    exit 1;                                            \
	fi

install_build_deps:
	echo "Nothing to install"
