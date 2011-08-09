VERSION = 0.1.$(shell date +%Y%m%d%H%M%S)
RELEASE = 1

cleandist:
	rm -rf dist
	mkdir dist

production:
	
tarball:
	rm -f MANIFEST
	for file in hydra-agent.spec setup.py; do \
		sed -e 's/@VERSION@/$(VERSION)/g' < $$file.in > $$file; \
	done
	python setup.py sdist

rpms: production cleandist tarball
	rm -rf _topdir
	mkdir -p _topdir/{BUILD,S{PEC,OURCE,RPM}S,RPMS/noarch}
	cp dist/hydra-agent-$(VERSION).tar.gz _topdir/SOURCES
	cp hydra-agent.spec _topdir/SPECS
	rpmbuild -bb --define "_topdir $$(pwd)/_topdir" _topdir/SPECS/hydra-agent.spec
	mv _topdir/RPMS/noarch/hydra-agent-$(VERSION)-$(RELEASE).noarch.rpm dist/
	rm -rf _topdir

install:
	install -d -p $(DESTDIR)/root/
	cp -a hydra-{agent,rmmod}.py $(DESTDIR)/root/
