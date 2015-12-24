EL_MAJOR = $(shell rpm --eval '%{?rhel}')

SRC_REPO = http://dl.fedoraproject.org/pub/epel/$(EL_MAJOR)/x86_64/

ifeq ($(EL_MAJOR), 7)
INITIAL_IN_TREE := true
ALL_RPMS       := pcapy-0.10.8-5.el7.x86_64.rpm \
                  python-daemon-1.6-4.el7.noarch.rpm \
                  python-lockfile-0.9.1-4.el7.noarch.rpm \
                  python-meld3-0.6.10-1.el7.x86_64.rpm \
                  python-ordereddict-1.1-6.el7.noarch.rpm \
                  python-simplejson-3.3.3-1.el7.x86_64.rpm \
                  v8-3.14.5.10-17.el7.x86_64.rpm \
                  nodejs-0.10.36-3.el7.x86_64.rpm \
                  http-parser-2.0-4.20121128gitcd01361.el7.x86_64.rpm \
                  libuv-0.10.34-1.el7.x86_64.rpm \
                  python-paramiko-1.15.1-1.el7.noarch.rpm \
                  python-crypto-2.6.1-1.el7.x86_64.rpm \
                  python-ecdsa-0.11-3.el7.noarch.rpm \
                  erlang-erts-R16B-03.11.el7.x86_64.rpm \
                  erlang-mnesia-R16B-03.11.el7.x86_64.rpm \
                  erlang-os_mon-R16B-03.11.el7.x86_64.rpm \
                  erlang-sasl-R16B-03.11.el7.x86_64.rpm \
                  erlang-xmerl-R16B-03.11.el7.x86_64.rpm \
                  erlang-asn1-R16B-03.11.el7.x86_64.rpm \
                  erlang-compiler-R16B-03.11.el7.x86_64.rpm \
                  erlang-crypto-R16B-03.11.el7.x86_64.rpm \
                  erlang-hipe-R16B-03.11.el7.x86_64.rpm \
                  erlang-inets-R16B-03.11.el7.x86_64.rpm \
                  erlang-kernel-R16B-03.11.el7.x86_64.rpm \
                  erlang-otp_mibs-R16B-03.11.el7.x86_64.rpm \
                  erlang-public_key-R16B-03.11.el7.x86_64.rpm \
                  erlang-runtime_tools-R16B-03.11.el7.x86_64.rpm \
                  erlang-snmp-R16B-03.11.el7.x86_64.rpm \
                  erlang-ssl-R16B-03.11.el7.x86_64.rpm \
                  erlang-stdlib-R16B-03.11.el7.x86_64.rpm \
                  erlang-syntax_tools-R16B-03.11.el7.x86_64.rpm \
                  erlang-tools-R16B-03.11.el7.x86_64.rpm
# this python-daemon silliness is because, bucking convention (and avoiding
# duplication), there is an actual pypi package named python-daemon and there
# is a heuristic in all of this requirements generation to remove any leading
# python- from package names supplied in $(ALL_RPMS)
REQUIREMENTS   += pycrypto==2.6.1 python-daemon==1.6
NO_REQUIREMENT += python-crypto erlang-erts erlang-mnesia erlang-os_mon \
                  erlang-sasl erlang-xmerl erlang-asn1 erlang-compiler \
                  erlang-crypto erlang-hipe erlang-inets erlang-kernel \
                  erlang-otp_mibs erlang-public_key erlang-runtime_tools \
                  erlang-snmp erlang-ssl erlang-stdlib erlang-syntax_tools \
                  erlang-tools python-simplejson
else
ALL_RPMS       := pcapy-0.10.5-6.el6.x86_64.rpm \
                  python-argparse-1.2.1-2.el6.noarch.rpm \
                  python-daemon-1.5.2-1.el6.noarch.rpm \
                  python-importlib-1.0.2-1.el6.noarch.rpm \
                  python-lockfile-0.8-3.el6.noarch.rpm \
                  python-meld3-0.6.7-1.el6.x86_64.rpm \
                  python-ordereddict-1.1-2.el6.noarch.rpm \
                  v8-3.14.5.10-14.el6.x86_64.rpm \
                  nodejs-0.10.33-1.el6.x86_64.rpm \
                  http-parser-2.0-4.20121128gitcd01361.el6.x86_64.rpm \
                  libuv-0.10.29-1.el6.x86_64.rpm \
                  c-ares19-1.9.1-5.el6.3.x86_64.rpm \
                  python-gunicorn-18.0-1.el6.noarch.rpm
REQUIREMENTS   += python-daemon==1.5.2
NO_REQUIREMENT += c-ares19 
endif

NO_REQUIREMENT += pcapy python-daemon v8 nodejs http-parser libuv

include ../include/Makefile.fetch-from-repo
