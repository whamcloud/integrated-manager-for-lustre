
VERSION := $(shell echo 0.4.`date -u +%Y%m%d%H%M`.`git rev-parse --short HEAD`)

RELEASE := 1

cleandist:
	rm -rf  dist
	mkdir dist

version:
	echo 'VERSION = "$(VERSION)"' > production_version.py

develop: version
	python setup.py develop

tarball: version
	rm -f MANIFEST
	sed -e 's/@VERSION@/$(VERSION)/g' \
	    -e 's/@RELEASE@/$(RELEASE)/g' \
	< chroma-manager.spec.in > chroma-manager.spec
	# workaround setuptools
	touch .chroma-manager.wsgi
	python setup.py sdist
	rm -f .chroma-manager.wsgi

rpms: cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/chroma-manager-$(VERSION).tar.gz _topdir/SOURCES
	cp chroma-storage-init.sh chroma-worker-init.sh chroma-host-discover-init.sh chroma-manager.conf logrotate.cfg _topdir/SOURCES
	cp chroma-manager.spec _topdir/SPECS
	rpmbuild -bb --define "_topdir $$(pwd)/_topdir" _topdir/SPECS/chroma-manager.spec
	mv _topdir/RPMS/noarch/chroma-manager-*$(VERSION)-$(RELEASE).noarch.rpm dist/
	rm -rf _topdir

docs:
	virtualenv myenv
	cd myenv; \
	. bin/activate; \
	pip install -r ../requirements.txt; \
	cd ../docs; \
	make SPHINXBUILD="$$PWD/../myenv/bin/sphinx-build"

.PHONY: docs
