import pkg_resources

try:
    PACKAGE_VERSION = pkg_resources.get_distribution("emf-manager").version
except pkg_resources.DistributionNotFound:
    PACKAGE_VERSION = "0.0.0"

VERSION = "{}-1".format(PACKAGE_VERSION)
BUILD = ""
IS_RELEASE = True
