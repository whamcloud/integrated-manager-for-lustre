VERSION = 1.16.1
RELEASE = 2
SRC_REPO = https://kojipkgs.fedoraproject.org/packages/python-paramiko/$(VERSION)/$(RELEASE).el7/noarch/

ALL_RPMS = python2-paramiko-$(VERSION)-$(RELEASE).el7.noarch.rpm

REQUIREMENTS   = paramiko==$(VERSION)
NO_REQUIREMENT = python2-paramiko

include ../include/Makefile.fetch-from-repo
