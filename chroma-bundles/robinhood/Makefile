RPMS		:= robinhood-webgui robinhood-lhsm robinhood-adm
EXCLUDES	:= lustre-client
DESC		:= Robinhood Policy Engine
VERSION		:= $(shell rpm --qf '%{version}' -qp $(REPO)/robinhood-adm-[0-9]*.rpm)

include ../include/Makefile.bundle
