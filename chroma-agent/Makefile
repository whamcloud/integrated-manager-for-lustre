VERSION := $(shell python -c 'from chroma_agent import __version__; print __version__')
ifeq ($(origin RELEASE), undefined)
  RELEASE := $(shell echo `date +%Y%m%d%H%M`_`git rev-parse --short HEAD`)
endif


all: rpms

cleandist:
	rm -rf dist
	mkdir dist

production:
	
tarball:
	rm -f MANIFEST
	python setup.py sdist

rpms: production cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/chroma-agent-*.tar.gz _topdir/SOURCES
	cp chroma-agent-init.sh _topdir/SOURCES
	cp chroma-agent.spec _topdir/SPECS
	rpmbuild --define "_topdir $$(pwd)/_topdir" \
		--define "version $(VERSION)" \
		--define "release $(RELEASE)" \
		-bb _topdir/SPECS/chroma-agent.spec
	mv _topdir/RPMS/noarch/chroma-agent-*.noarch.rpm dist/
	rm -rf _topdir

docs:
	@echo "Nothing to do here"
