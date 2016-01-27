LOCATION := http://pypi.python.org/packages/source/g/greenlet/greenlet-0.4.0.zip
TARBALL_EXT := zip
USES_DISTUTILS = true

# Note: we remove optimisation by supplying -O0 to python setup.py install command (spec.ed) in order to avoid
#       greenlet / gcc 4.8 incompatibility
include ../include/Makefile.rpm-from-tarball
