tarball:
	python setup.py sdist

rpms: tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/hydra-server-0.1.tar.gz _topdir/SOURCES
	cp hydra-monitor-init.sh hydra-server.conf _topdir/SOURCES
	cp hydra-server.spec _topdir/SPECS
	rpmbuild -bb --define "_topdir $$(pwd)/_topdir" _topdir/SPECS/hydra-server.spec
	mv _topdir/RPMS/noarch/hydra-server-0.1-1.noarch.rpm dist/
	rm -rf _topdir

install:
	#install -d -p $(DESTDIR)/etc/hydra-server
	#cp -a settings.py $(DESTDIR)/etc/hydra-server
	install -d -p $(DESTDIR)/usr/share/hydra-server
	cp -a collections_24.py __init__.py manage.py monitor monitor.wsgi settings.py urls.py $(DESTDIR)/usr/share/hydra-server
