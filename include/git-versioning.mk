space :=
space +=
SCM_COMMIT_NUMBER	:= $(shell git rev-list HEAD | wc -l)
ifeq ($(strip $(JOB_NAME)),)
JENKINS_BUILD_TAG	:=
else
JENKINS_BUILD_TAG	:= $(shell echo .jenkins-$(JOB_NAME)-$(BUILD_NUMBER) | \
                                   sed -e 's/arch=[^,-]*,\?-\?//' \
                                       -e 's/distro=[^,-]*,\?-\?//' \
                                       -e 's,[/-],_,g')
endif
SCM_DESCRIPTION		:= $(shell msg=$$(git log -n 1 --abbrev-commit); \
                                   if echo "$$msg" | \
                                   grep -q "^    Create-Tag:"; then \
                                   echo "$$msg" | \
                                   sed -ne '/^    Create-Tag:/s/RC[0-9]*//;s/^.*: *v//p;/^    Create-Tag:/s/P[0-9]*//'; fi)
ifeq ($(strip $(SCM_DESCRIPTION)),)
SCM_DESCRIPTION		:= $(subst -,$(space),$(shell git describe --tags \
                                                      --match v[0-9]* | \
                                                      sed -e 's/^v//' \
                                                          -e 's/RC[0-9]*//' \
                                                          -e 's/P[0-9]*//'))
endif

# Stable variable names exported to packaging and code
BUILD_NUMBER		:= $(SCM_COMMIT_NUMBER)
VERSION			:= $(subst $(space),-,$(SCM_DESCRIPTION))
PACKAGE_VERSION		:= $(word 1, $(SCM_DESCRIPTION))
PACKAGE_RELEASE		:= $(subst $(space),.,$(wordlist 2, 10, $(SCM_DESCRIPTION)))
ifeq ($(strip $(PACKAGE_RELEASE)),)
	IS_RELEASE := True
	# We use the build number in a package's release field in
	# order to distinguish between RCs with identical version fields.
	# e.g. 2.0.0.0-2983 (RC1), 2.0.0.0-2987 (RC2)
	# The important thing is that newer RCs must upgrade older ones,
	# and end-users only really care about the %{version} field.
	PACKAGE_RELEASE := $(BUILD_NUMBER)
else
	IS_RELEASE := False
	# In development, we embed the rest of the git describe output
	# in order to easily understand the provenance of a package.
	# The commits-since-tag number will ensure that newer packages
	# are preferred, since RPM's version parsing works left-to-right.
	PACKAGE_RELEASE := $(BUILD_NUMBER).$(PACKAGE_RELEASE)$(JENKINS_BUILD_TAG)

	# Display this in the UI to make ID easier in dev/test
	BUILD_NUMBER := $(JENKINS_BUILD_TAG)
endif

MODULE_SUBDIR ?= $(subst -,_,$(NAME))

# only overwrite scm_version.py if we have info from git
ifneq ($(strip $(PACKAGE_VERSION)),)
$(shell { echo 'VERSION = "$(VERSION)"';                                    \
	  echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"';                    \
	  echo 'BUILD = "$(BUILD_NUMBER)"';                                 \
	  echo 'IS_RELEASE = $(IS_RELEASE)'; } > scm_version.py.tmp;        \
	  trap 'rm -f scm_version.py.tmp' EXIT;                             \
	  if ! cmp scm_version.py.tmp $(MODULE_SUBDIR)/scm_version.py; then \
	      cp scm_version.py.tmp $(MODULE_SUBDIR)/scm_version.py;        \
	  fi)
endif
