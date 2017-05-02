include ../include/Makefile.distro

SRC_REPO = http://dl.fedoraproject.org/pub/epel/$(EL_MAJOR)/x86_64/

ifeq ($(EL_MAJOR), 7)
INITIAL_IN_TREE := true
ALL_RPMS       := pcapy-0.10.8-5.el7.x86_64.rpm                  \
                  python-daemon-1.6-4.el7.noarch.rpm             \
                  python-lockfile-0.9.1-4.el7.noarch.rpm         \
                  python-meld3-0.6.10-1.el7.x86_64.rpm           \
                  python-ordereddict-1.1-6.el7.noarch.rpm        \
                  python-anyjson-0.3.3-3.el7.noarch.rpm          \
                  python2-paramiko-1.16.1-2.el7.noarch.rpm       \
                  python2-crypto-2.6.1-13.el7.x86_64.rpm         \
                  libtomcrypt-1.17-23.el7.x86_64.rpm             \
                  libtommath-0.42.0-4.el7.x86_64.rpm             \
                  python2-ecdsa-0.13-4.el7.noarch.rpm            \
                  erlang-erts-R16B-03.11.el7.x86_64.rpm          \
                  erlang-mnesia-R16B-03.11.el7.x86_64.rpm        \
                  erlang-os_mon-R16B-03.11.el7.x86_64.rpm        \
                  erlang-sasl-R16B-03.11.el7.x86_64.rpm          \
                  erlang-xmerl-R16B-03.11.el7.x86_64.rpm         \
                  erlang-asn1-R16B-03.11.el7.x86_64.rpm          \
                  erlang-compiler-R16B-03.11.el7.x86_64.rpm      \
                  erlang-crypto-R16B-03.11.el7.x86_64.rpm        \
                  erlang-hipe-R16B-03.11.el7.x86_64.rpm          \
                  erlang-inets-R16B-03.11.el7.x86_64.rpm         \
                  erlang-kernel-R16B-03.11.el7.x86_64.rpm        \
                  erlang-otp_mibs-R16B-03.11.el7.x86_64.rpm      \
                  erlang-public_key-R16B-03.11.el7.x86_64.rpm    \
                  erlang-runtime_tools-R16B-03.11.el7.x86_64.rpm \
                  erlang-snmp-R16B-03.11.el7.x86_64.rpm          \
                  erlang-ssl-R16B-03.11.el7.x86_64.rpm           \
                  erlang-stdlib-R16B-03.11.el7.x86_64.rpm        \
                  erlang-syntax_tools-R16B-03.11.el7.x86_64.rpm  \
                  erlang-tools-R16B-03.11.el7.x86_64.rpm
# this python-daemon silliness is because, bucking convention (and avoiding
# duplication), there is an actual pypi package named python-daemon and there
# is a heuristic in all of this requirements generation to remove any leading
# python- from package names supplied in $(ALL_RPMS)
REQUIREMENTS   += pycrypto==2.6.1 python-daemon==1.6 paramiko==1.16.1
NO_REQUIREMENT += python2-crypto python2-ecdsa python2-paramiko             \
                  erlang-erts erlang-mnesia erlang-os_mon erlang-sasl       \
                  erlang-xmerl erlang-asn1 erlang-compiler erlang-crypto    \
                  erlang-hipe erlang-inets erlang-kernel erlang-otp_mibs    \
                  erlang-public_key erlang-runtime_tools erlang-snmp        \
                  erlang-ssl erlang-stdlib erlang-syntax_tools erlang-tools \
                  libtomcrypt libtommath
else ifeq ($(EL_MAJOR), 6)
ALL_RPMS       := pcapy-0.10.5-6.el6.x86_64.rpm                 \
                  python-argparse-1.2.1-2.el6.noarch.rpm        \
                  python-daemon-1.5.2-1.el6.noarch.rpm          \
                  python-importlib-1.0.2-1.el6.noarch.rpm       \
                  python-lockfile-0.8-3.el6.noarch.rpm          \
                  python-meld3-0.6.7-1.el6.x86_64.rpm           \
                  python-ordereddict-1.1-2.el6.noarch.rpm       \
                  python-anyjson-0.3.3-1.el6.noarch.rpm         \
                  python-gunicorn-18.0-1.el6.noarch.rpm         \
                  erlang-erts-R14B-04.3.el6.x86_64.rpm          \
                  erlang-mnesia-R14B-04.3.el6.x86_64.rpm        \
                  erlang-os_mon-R14B-04.3.el6.x86_64.rpm        \
                  erlang-sasl-R14B-04.3.el6.x86_64.rpm          \
                  erlang-xmerl-R14B-04.3.el6.x86_64.rpm         \
                  erlang-asn1-R14B-04.3.el6.x86_64.rpm          \
                  erlang-compiler-R14B-04.3.el6.x86_64.rpm      \
                  erlang-crypto-R14B-04.3.el6.x86_64.rpm        \
                  erlang-hipe-R14B-04.3.el6.x86_64.rpm          \
                  erlang-inets-R14B-04.3.el6.x86_64.rpm         \
                  erlang-kernel-R14B-04.3.el6.x86_64.rpm        \
                  erlang-otp_mibs-R14B-04.3.el6.x86_64.rpm      \
                  erlang-public_key-R14B-04.3.el6.x86_64.rpm    \
                  erlang-runtime_tools-R14B-04.3.el6.x86_64.rpm \
                  erlang-snmp-R14B-04.3.el6.x86_64.rpm          \
                  erlang-ssl-R14B-04.3.el6.x86_64.rpm           \
                  erlang-stdlib-R14B-04.3.el6.x86_64.rpm        \
                  erlang-syntax_tools-R14B-04.3.el6.x86_64.rpm  \
                  erlang-webtool-R14B-04.3.el6.x86_64.rpm       \
                  erlang-tools-R14B-04.3.el6.x86_64.rpm         \
                  erlang-et-R14B-04.3.el6.x86_64.rpm            \
                  erlang-gs-R14B-04.3.el6.x86_64.rpm            \
                  erlang-wx-R14B-04.3.el6.x86_64.rpm            \
                  erlang-observer-R14B-04.3.el6.x86_64.rpm      \
                  wxBase-2.8.12-1.el6.x86_64.rpm                \
                  wxGTK-2.8.12-1.el6.x86_64.rpm                 \
                  wxGTK-gl-2.8.12-1.el6.x86_64.rpm
REQUIREMENTS   += python-daemon==1.5.2
else
$(error "Unknown major el version $(EL_MAJOR)")
endif

NO_REQUIREMENT += pcapy python-daemon                                      \
                  erlang-erts erlang-mnesia erlang-os_mon                  \
                  erlang-sasl erlang-xmerl erlang-asn1 erlang-compiler     \
                  erlang-crypto erlang-hipe erlang-inets erlang-kernel     \
                  erlang-otp_mibs erlang-public_key erlang-runtime_tools   \
                  erlang-snmp erlang-ssl erlang-stdlib erlang-syntax_tools \
                  erlang-webtool erlang-tools erlang-et erlang-gs          \
                  erlang-wx erlang-observer                                \
                  wxBase wxGTK wxGTK-gl

include ../include/Makefile.fetch-from-repo
