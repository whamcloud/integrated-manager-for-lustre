VERSION := $(shell python -c 'from hydra_agent import __version__; print __version__')
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
	cp dist/hydra-agent-*.tar.gz _topdir/SOURCES
	cp hydra-agent-init.sh _topdir/SOURCES
	cp hydra-agent.spec _topdir/SPECS
	rpmbuild --define "_topdir $$(pwd)/_topdir" \
		--define "version $(VERSION)" \
		--define "release $(RELEASE)" \
		-bb _topdir/SPECS/hydra-agent.spec
	mv _topdir/RPMS/noarch/hydra-agent-*.noarch.rpm dist/
	rm -rf _topdir

docs:
	@echo "Nothing to do here"
