DEV_REPO ?= $(shell PYTHONPATH=$(CURDIR)../chroma-manager python -c 'import settings; print settings.DEV_REPO_PATH')

include ../include/Makefile.version

# In development, we want to stop at first failure, but when running
# in a Jenkins job we want all the gory details.
ifdef JENKINS_URL
    NOSE_ARGS ?= --with-xunit --xunit-file=chroma-agent-unit-test-results.xml --with-coverage
else
    NOSE_ARGS ?=
endif

all: rpms

version:
	echo 'VERSION = "$(VERSION)"' > chroma_agent/scm_version.py
	echo 'PACKAGE_VERSION = "$(PACKAGE_VERSION)"' >> chroma_agent/scm_version.py
	echo 'BUILD = "$(BUILD_NUMBER)"' >> chroma_agent/scm_version.py
	echo 'IS_RELEASE = $(IS_RELEASE)' >> chroma_agent/scm_version.py

develop: version
	python setup.py develop

cleandist:
	rm -rf dist
	mkdir dist

production:
	
tarball: version
	rm -f MANIFEST
	python setup.py sdist

rpms: production cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/chroma-agent-*.tar.gz _topdir/SOURCES
	cp chroma-agent-init.sh lustre-modules-init.sh logrotate.cfg \
	   start-copytools.conf copytool.conf                        \
	   start-copytool-monitors.conf copytool-monitor.conf        \
	   _topdir/SOURCES
	cp chroma-agent.spec _topdir/SPECS
	dist=$$(rpm --eval %dist);                             \
	dist=$${dist/.centos/};                                \
	rpmbuild --define "_topdir $$(pwd)/_topdir"            \
		 --define "version $(PACKAGE_VERSION)"         \
		 --define "package_release $(PACKAGE_RELEASE)" \
		 --define "%dist $$dist"                       \
		 -bb _topdir/SPECS/chroma-agent.spec
	mv _topdir/RPMS/noarch/chroma-agent-*.noarch.rpm dist/
	rm -rf _topdir

docs download:
	@echo "Nothing to do here"

test:
	@nosetests $(NOSE_ARGS)

update_repo: rpms
	@echo "Updating dev repo with new RPMs..."
	rm -f $(DEV_REPO)/chroma-agent/chroma-agent-*.rpm
	cp -a dist/chroma-agent-*.rpm $(DEV_REPO)/chroma-agent
	cd $(DEV_REPO) && createrepo --pretty .
