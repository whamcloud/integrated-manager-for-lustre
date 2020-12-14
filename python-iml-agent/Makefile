rpms::
	rm -rf _topdir *.rpm
	mkdir -p _topdir/SOURCES/
	python setup.py sdist -d _topdir/SOURCES/
	rpmbuild -ba -D "%_topdir ${PWD}/_topdir" python-iml-agent.spec
	cp -l _topdir/RPMS/*/*.rpm ./

repo:: rpms
	(cd _topdir/RPMS; createrepo .)

clean::
	python setup.py clean
	rm -f *~

extraclean:: clean
	python setup.py clean --all
	rm -rf _topdir/ dist/
	rm -f *.rpm
