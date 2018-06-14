CLEAN        += $(NAME)-$(PACKAGE_VERSION).tgz \
	        $(subst iml-,,$(NAME)-$(PACKAGE_VERSION).tgz) targetdir

include include/common.mk

TARGET_RPMS = $(NAME)-$(PACKAGE_VERSION)-$(PACKAGE_RELEASE)$(RPM_DIST).noarch.rpm

include include/rpm-common.mk
include include/copr.mk

# these are interesting ways to try to generate the prerequisite list but
# they don't quite work since prerequisite determination is done at Makefile
# reading time, not when this recipe is evaluated, which is what needs to
# happen in order to generate the list of files *after* the .html files are
# generated
# worth keeping here for future reference
# $(shell npx npm-packlist-cli -o make 2>/dev/null)
# this one needs:
# SHELL := /bin/bash
# $(shell find | grep -v -f <(echo "\.sw."; echo ".npmignore"; echo "^.$$"; echo "^.\/.git"; sed -e 's/\/$$//' -e 's/\*/.*/g' -e 's/^/^.\//' .npmignore) | sed -e 's/^\.\///' -e 's/ /\\ /g')
$(NAME)-$(PACKAGE_VERSION).tgz: $(NPM_PREREQS) package.json LICENSE
	npm pack

$(subst iml-,,$(NAME)-$(PACKAGE_VERSION).tgz): $(NAME)-$(PACKAGE_VERSION).tgz
	rm -f $@
	ln $^ $@

.PHONY: install_build_deps clean distclean
