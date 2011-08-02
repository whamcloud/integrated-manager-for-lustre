VERSION = 0.3.$(shell date +%Y%m%d%H%M%S)
RELEASE = 1

cleandist:
	rm -rf  dist
	mkdir dist

production:
	echo -e "/^DEBUG =/s/= .*$$/= False/\nwq" | ed settings.py
	
tarball:
	rm -f MANIFEST
	echo -e "/^      version =/s/ '.*',$$/ '$(VERSION)',/\nwq" | ed setup.py
	echo -e "/^%define version /s/ version .*$$/ version $(VERSION)/\nwq" | ed hydra-server.spec
	echo -e "/^%define unmangled_version /s/_version .*$$/_version $(VERSION)/\nwq" | ed hydra-server.spec
	python setup.py sdist

rpms: production cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/hydra-server-$(VERSION).tar.gz _topdir/SOURCES
	cp hydra-worker-init.sh hydra-server.conf _topdir/SOURCES
	cp hydra-server.spec _topdir/SPECS
	rpmbuild -bb --define "_topdir $$(pwd)/_topdir" _topdir/SPECS/hydra-server.spec
	mv _topdir/RPMS/noarch/hydra-server-$(VERSION)-$(RELEASE).noarch.rpm dist/
	rm -rf _topdir

install:
	#install -d -p $(DESTDIR)/etc/hydra-server
	#cp -a settings.py $(DESTDIR)/etc/hydra-server
	install -d -p $(DESTDIR)/usr/share/hydra-server
	cp -a collections_24.py __init__.py manage.py middleware.py monitor monitor.wsgi polymorphic settings.py urls.py $(DESTDIR)/usr/share/hydra-server
