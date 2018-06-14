RPM_SPEC := python-$(NAME).spec

TARGET_RPMS = $(addprefix _topdir/RPMS/noarch/python-,  \
                $(addsuffix -$(PACKAGE_VRD).noarch.rpm, \
                  $(ALL_PKGS)))

test_dependencies:
	test_deps="$(TEST_DEPS)";                               \
	if rpm --version && yum --version &&                    \
	   ! rpm -q $$test_deps >/dev/null 2>&1; then           \
	    echo "Some dependencies need installing...";        \
	    echo "You will need sudo root privilledges for yum" \
	    sudo yum -y install $$test_deps;                    \
	fi

test: test_dependencies
	@nosetests $(NOSE_ARGS)
