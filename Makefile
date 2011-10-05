VERSION := $(shell python -c 'from r3d import __version__; print __version__')
ifeq ($(origin RELEASE), undefined)
  RELEASE := $(shell date +%Y%m%d%H%M%S)
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
	cp dist/django-r3d-*.tar.gz _topdir/SOURCES
	cp django-r3d.spec _topdir/SPECS
	rpmbuild --define "_topdir $$(pwd)/_topdir" \
		--define "version $(VERSION)" \
		--define "release $(RELEASE)" \
		-bb _topdir/SPECS/django-r3d.spec
	mv _topdir/RPMS/noarch/django-r3d-*.noarch.rpm dist/
	rm -rf _topdir MANIFEST
