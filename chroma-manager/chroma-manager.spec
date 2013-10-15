%{!?name: %define name chroma-manager}
%{?!version: %define version %(%{__python} -c "from scm_version import PACKAGE_VERSION; sys.stdout.write(PACKAGE_VERSION)")}
%{?!release: %define release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

# The install directory for the manager
%{?!manager_root: %define manager_root /usr/share/chroma-manager}

Summary: The Intel Manager for Lustre Monitoring and Adminisration Interface
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
Source1: chroma-manager.conf
Source2: chroma-supervisor-init.sh
Source3: chroma-host-discover-init.sh
Source4: logrotate.cfg
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Intel Corporation <hpdd-info@intel.com>
Url: http://lustre.intel.com/
BuildRequires: python-setuptools
Requires: mod_wsgi mod_ssl httpd ntp ed
Requires: python-setuptools
Requires: python-prettytable
Requires: python-dse
Requires: python-supervisor
Requires: python-jsonschema
Requires: python-dateutil
Requires: python-uuid
Requires: python-paramiko
Requires: python-kombu >= 2.4.7
Requires: python-daemon
Requires: python-requests >= 1.0.0
Requires: python-celery >= 3.0.11
Requires: python-amqplib
Requires: python-networkx
Requires: python-httpagentparser
Requires: pygobject2
Requires: postgresql-server
Requires: python-psycopg2
Requires: rabbitmq-server
Requires: avahi-dnsconfd
Requires: avahi-python
Requires: Django >= 1.4
Requires: Django-south >= 0.7.4
Requires: django-tastypie = 0.9.11
Requires: django-celery >= 3.0.10
Requires: django-picklefield
Requires: chroma-manager-libs = %{version}
Requires: chroma-manager-cli = %{version}
Requires: chroma-diagnostics >= %{version}
Requires: policycoreutils-python
Requires: python-gevent >= 0.13
Requires: fence-agents-iml > 3.1.5-25.wc1.el6.2
Requires: system-config-firewall-base
Conflicts: chroma-agent
Requires(post): selinux-policy-targeted

%description
This is the Intel Manager for Lustre Monitoring and Adminstration Interface

%package libs
Summary: Common libraries for Chroma Server
Group: System/Libraries
%description libs
This package contains libraries for Chroma CLI and Chroma Server.

%package cli
Summary: Command-Line Interface for Chroma Server
Group: System/Utility
Requires: chroma-manager-libs = %{version} python-argparse python-requests >= 1.0.3 python-tablib python-dateutil python-prettytable
%description cli
This package contains the Chroma CLI which can be used on a Chroma server
or on a separate node.

%package integration-tests
Summary: Chroma Manager Integration Tests
Group: Development/Tools
Requires: python-dateutil python-requests python-nose python-nose-testconfig python-paramiko python-django
%description integration-tests
This package contains the Chroma Manager integration tests and scripts and is intended
to be used by the Chroma test framework.

%package devel
Summary: Contains stripped .py files
Group: Development
Requires: %{name} = %{version}-%{release}
%description devel
This package contains the .py files stripped out of the production build.

%prep
%setup -n %{name}-%{version}
echo -e "/^DEBUG =/s/= .*$/= False/\nwq" | ed settings.py 2>/dev/null
echo -e "/^HTTPS_FRONTEND_PORT =/s/= .*$/= 443/\nwq" | ed settings.py 2>/dev/null

%build
%{__python} setup.py build
# workaround setuptools inanity for top-level datafiles
cp -a chroma-manager.wsgi build/lib
cp -a production_supervisord.conf build/lib

%install
%{__python} setup.py install --skip-build --root=%{buildroot}
install -d -p $RPM_BUILD_ROOT%{manager_root}
mv $RPM_BUILD_ROOT/%{python_sitelib}/* $RPM_BUILD_ROOT%{manager_root}
# Do a little dance to get the egg-info in place
mv $RPM_BUILD_ROOT%{manager_root}/*.egg-info $RPM_BUILD_ROOT/%{python_sitelib}
mkdir -p $RPM_BUILD_ROOT/etc/{init,logrotate,httpd/conf}.d
cp %{SOURCE1} $RPM_BUILD_ROOT/etc/httpd/conf.d/chroma-manager.conf
cp %{SOURCE2} $RPM_BUILD_ROOT/etc/init.d/chroma-supervisor
cp %{SOURCE3} $RPM_BUILD_ROOT/etc/init.d/chroma-host-discover
install -m 644 %{SOURCE4} $RPM_BUILD_ROOT/etc/logrotate.d/chroma-manager

# Nuke source code (HYD-1849), but preserve key .py files needed for operation
preserve_patterns="settings.py manage.py chroma_core/migrations/*.py chroma_core/management/commands/*.py"

# Stash .py files for -devel package
find $RPM_BUILD_ROOT%{manager_root}/ -name "*.py" \
    | sed -e "s,$RPM_BUILD_ROOT,," > devel.files

# only include compiled modules in the main package
for manager_file in $(find $RPM_BUILD_ROOT%{manager_root}/ -name "*.pyc"); do
    install_file=${manager_file/$RPM_BUILD_ROOT\///}
    echo "${install_file%.py*}.py[c,o]" >> manager.files
done

# ... except for these files which are required for operation
for pattern in $preserve_patterns; do
    echo "%{manager_root}/$pattern" >> manager.files
done

# This is fugly, but it's cleaner than moving things around to get our
# modules in the standard path.
entry_scripts="/usr/bin/chroma-config /usr/bin/chroma"
for script in $entry_scripts; do
  ed $RPM_BUILD_ROOT$script <<EOF
/import load_entry_point/ a
sys.path.insert(0, "%{manager_root}")
.
w
q
EOF
done

%clean
rm -rf $RPM_BUILD_ROOT

%post
ed /etc/httpd/conf.d/wsgi.conf <<EOF 2>/dev/null
/^#LoadModule /s/^#\(LoadModule wsgi_module modules\/mod_wsgi.so\)/\1/
w
q
EOF

# Start apache which should present a helpful setup
# page if the user visits it before configuring Chroma fully
chkconfig httpd on

# Pre-create log files to set permissions
mkdir -p /var/log/chroma
chown -R apache:apache /var/log/chroma

# This is required for opening connections between
# httpd and rabbitmq-server
setsebool -P httpd_can_network_connect 1 2>/dev/null

# This is required because of bad behaviour in python's 'uuid'
# module (see HYD-1475)
setsebool -P httpd_tmp_exec 1 2>/dev/null

# This is required for apache to serve HTTP_API_PORT
semanage port -a -t http_port_t -p tcp 8001

if ! out=$(service iptables status) || [ "$out" = "Table: filter
Chain INPUT (policy ACCEPT)
num  target     prot opt source               destination

Chain FORWARD (policy ACCEPT)
num  target     prot opt source               destination

Chain OUTPUT (policy ACCEPT)
num  target     prot opt source               destination         " ]; then
    arg="-n"
else
    arg=""
fi
if [ $1 -lt 2 ]; then
    # open ports in the firewall for access to the manager
    for port in 80 443; do
        lokkit $arg -p $port:tcp
    done
fi

echo "Thank you for installing Chroma.  To complete your installation, please"
echo "run \"chroma-config setup\""

%preun
service chroma-supervisor stop
# remove the /static/ dir of files that was created by Django's collectstatic
rm -rf %{manager_root}/static

%postun
if [ $1 -lt 1 ]; then
    # close previously opened ports in the firewall for access to the manager
    sed -i \
        -e '/INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT/d'\
        -e '/INPUT -m state --state NEW -m tcp -p tcp --dport 443 -j ACCEPT/d' \
        -e '/INPUT -m state --state NEW -m udp -p udp --dport 123 -j ACCEPT/d' \
        /etc/sysconfig/iptables
    sed -i -e '/--port=80:tcp/d' -e '/--port=443:tcp/d' \
           -e '/--port=123:udp/d' /etc/sysconfig/system-config-firewall

    # clean out /var/lib/chroma
    if [ -d /var/lib/chroma ]; then
        rm -rf /var/lib/chroma
    fi
fi

%files -f manager.files
%defattr(-,root,root)
%{_bindir}/chroma-host-discover
%{_bindir}/chroma-config
%dir %attr(0755,apache,apache)%{manager_root}
/etc/httpd/conf.d/chroma-manager.conf
%attr(0755,root,root)/etc/init.d/chroma-supervisor
%attr(0755,root,root)/etc/init.d/chroma-host-discover
%attr(0644,root,root)/etc/logrotate.d/chroma-manager
%attr(0755,root,root)%{manager_root}/manage.pyc
%{manager_root}/*.conf
%{manager_root}/*.wsgi
%{manager_root}/chroma_ui/templates/*
%{manager_root}/chroma_ui/static/*
%{manager_root}/chroma_help/*
%{manager_root}/chroma_core/fixtures/*
%{manager_root}/polymorphic/COPYING
# Stuff below goes into the -cli/-lib packages
%exclude %{manager_root}/chroma_cli
%exclude %{python_sitelib}/*.egg-info/
# will go into the -tests packages
%exclude %{manager_root}/example_storage_plugin_package
%exclude %{manager_root}/tests
%doc licenses/*

%files libs
%{python_sitelib}/*.egg-info/*

%files cli
%defattr(-,root,root)
%{_bindir}/chroma
%{manager_root}/chroma_cli/*

%files integration-tests
%defattr(-,root,root)
%{manager_root}/tests/__init__.pyc
%{manager_root}/tests/utils/*
%{manager_root}/tests/sample_data/*
%{manager_root}/tests/plugins/*
%{manager_root}/tests/integration/*
%attr(0755,root,root)%{manager_root}/tests/integration/run_tests

%files -f devel.files devel
%defattr(-,root,root)
