
VERSION := $(shell echo 0.3.`date -u +%Y%m%d%H%M`.`git rev-parse --short HEAD`)

RELEASE := 1

cleandist:
	rm -rf  dist
	mkdir dist

tarball:
	rm -f MANIFEST
	echo 'VERSION = "$(VERSION)"' > production_version.py
	for file in hydra-server.spec setup.py; do \
		sed -e 's/@VERSION@/$(VERSION)/g' \
		    -e 's/@RELEASE@/$(RELEASE)/g' \
		< $$file.in > $$file; \
	done
	python setup.py sdist

rpms: cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/hydra-server-$(VERSION).tar.gz _topdir/SOURCES
	cp hydra-storage-init.sh hydra-worker-init.sh hydra-host-discover-init.sh hydra-server.conf _topdir/SOURCES
	cp hydra-server.spec _topdir/SPECS
	rpmbuild -bb --define "_topdir $$(pwd)/_topdir" _topdir/SPECS/hydra-server.spec
	mv _topdir/RPMS/noarch/hydra-server-$(VERSION)-$(RELEASE).noarch.rpm dist/
	rm -rf _topdir

install:
	install -d -p $(DESTDIR)/usr/share/hydra-server
	cp -a __init__.py manage.py middleware.py benchmark chroma_api chroma_core chroma_ui monitor.wsgi polymorphic settings.py production_version.py urls.py $(DESTDIR)/usr/share/hydra-server
	install -d -m 755 $(DESTDIR)/usr/bin
	install -m 755 hydra-host-discover $(DESTDIR)/usr/bin
	install -m 755 chroma_core/bin/chroma-config $(DESTDIR)/usr/bin
