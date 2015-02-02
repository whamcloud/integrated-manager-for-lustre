SRC_REPO = http://dl.fedoraproject.org/pub/epel/6/x86_64/

ALL_RPMS = django-picklefield-0.1.9-2.el6.noarch.rpm Django-south-0.7.5-1.el6.noarch.rpm pcapy-0.10.5-6.el6.x86_64.rpm pyparsing-1.5.6-1.el6.noarch.rpm python-argparse-1.2.1-2.el6.noarch.rpm python-daemon-1.5.2-1.el6.noarch.rpm python-importlib-1.0.2-1.el6.noarch.rpm python-lockfile-0.8-3.el6.noarch.rpm python-meld3-0.6.7-1.el6.x86_64.rpm python-ordereddict-1.1-2.el6.noarch.rpm pdsh-rcmd-ssh-2.26-4.el6.x86_64.rpm pdsh-2.26-4.el6.x86_64.rpm v8-3.14.5.10-14.el6.x86_64.rpm nodejs-0.10.33-1.el6.x86_64.rpm http-parser-2.0-4.20121128gitcd01361.el6.x86_64.rpm libuv-0.10.29-1.el6.x86_64.rpm c-ares19-1.9.1-5.el6.3.x86_64.rpm
NO_REQUIREMENT = pcapy pdsh-rcmd-ssh pdsh Django-south python-daemon v8 nodejs http-parser libuv c-ares19
# unfortunately this hack (Django-south above and South==0.7.5 below) is needed
# because of the unfortunate naming convention of the South RPM
REQUIREMENTS = South==0.7.5 
# and this silliness is because, bucking convention (and avoiding duplication),
# there is an actual pypi package named python-daemon and there is a heuristic
# in all of this requirements generation to remove any leading python- from
# package names supplied in $(ALL_RPMS)
REQUIREMENTS += python-daemon==1.5.2
include ../include/Makefile.fetch-from-repo
