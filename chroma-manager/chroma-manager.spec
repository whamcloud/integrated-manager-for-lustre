%{!?name: %define name chroma-manager}
%{?!version: %define version %(%{__python} -c "from scm_version import PACKAGE_VERSION; sys.stdout.write(PACKAGE_VERSION)")}
%{?!package_release: %define package_release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

# The install directory for the manager
%{?!manager_root: %define manager_root /usr/share/chroma-manager}


Summary: The Intel Manager for Lustre Monitoring and Administration Interface
Name: %{name}
Version: %{version}
Release: %{package_release}%{?dist}
Source0: %{name}-%{version}.tar.gz
Source1: chroma-supervisor-init.sh
Source2: chroma-host-discover-init.sh
Source3: logrotate.cfg
Source4: chroma-config.1.gz
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
Vendor: Intel Corporation <hpdd-info@intel.com>
Url: http://lustre.intel.com/
BuildRequires: python-setuptools
Requires: python-setuptools
Requires: python-prettytable
Requires: python-dse
Requires: python-supervisor
Requires: python-jsonschema < 0.9.0
Requires: python-ordereddict
Requires: python-uuid
Requires: python-paramiko
Requires: python-kombu >= 3.0.19
Requires: python-daemon
Requires: python-requests >= 2.6.0
Requires: python-networkx
Requires: python-httpagentparser
Requires: python-gunicorn
Requires: pygobject2
Requires: postgresql-server
Requires: python-psycopg2
Requires: rabbitmq-server
Requires: ntp
Requires: Django >= 1.4, Django < 1.5
Requires: Django-south >= 0.7.4
Requires: django-tastypie = 0.9.11
Requires: django-picklefield
Requires: chroma-manager-libs = %{version}-%{release}
Requires: chroma-manager-cli = %{version}-%{release}
Requires: chroma-diagnostics >= %{version}-%{release}
Requires: policycoreutils-python
Requires: python-gevent >= 1.0.1
Requires: system-config-firewall-base
Requires: nodejs >= 1:6.9.4-2
Conflicts: chroma-agent
Requires(post): selinux-policy-targeted
Obsoletes: httpd
Obsoletes: mod_proxy_wstunnel
Obsoletes: mod_wsgi
Obsoletes: mod_ssl
Obsoletes: nodejs-active-x-obfuscator
Obsoletes: nodejs-bunyan
Obsoletes: nodejs-commander
Obsoletes: nodejs-nan
Obsoletes: nodejs-primus
Obsoletes: nodejs-primus-emitter
Obsoletes: nodejs-primus-multiplex
Obsoletes: nodejs-request
Obsoletes: nodejs-socket.io
Obsoletes: nodejs-socket.io-client
Obsoletes: nodejs-ws
Obsoletes: nodejs-tinycolor
Obsoletes: nodejs-extendable
Obsoletes: nodejs-xmlhttprequest
Obsoletes: nodejs-dotty
Obsoletes: nodejs-tough-cookie
Obsoletes: nodejs-options
Obsoletes: nodejs-punycode
Obsoletes: nodejs-load
Obsoletes: nodejs-json-stringify-safe
Obsoletes: nodejs-lodash
Obsoletes: nodejs-moment
Obsoletes: nodejs-q
Obsoletes: nodejs-qs
Obsoletes: nodejs-node-uuid
Obsoletes: nodejs-mime
Obsoletes: nodejs-base64id
Obsoletes: nodejs-policyfile
Obsoletes: nodejs-uritemplate
Obsoletes: nodejs-forever-agent
Obsoletes: nodejs-uglify-js
Obsoletes: nodejs-di
Obsoletes: nodejs-mv
Obsoletes: nodejs-json-mask
Obsoletes: nodejs-zeparser
Obsoletes: django-celery

%if 0%{?rhel} < 7
Requires: fence-agents-iml >= 3.1.5-48.wc1.el6.2
Requires: nginx >= 1.10.1-1
%endif

%if 0%{?rhel} > 6
Requires: fence-agents
Requires: fence-agents-virsh
Requires: nginx >= 1:1.10.1-1
%endif

%description
This is the Intel Manager for Lustre Monitoring and Administration Interface

%package libs
Summary: Common libraries for Chroma Server
Group: System/Libraries
%description libs
This package contains libraries for Chroma CLI and Chroma Server.

%package cli
Summary: Command-Line Interface for Chroma Server
Group: System/Utility
Requires: chroma-manager-libs = %{version}-%{release} python-argparse python-requests >= 2.6.0 python-tablib python-prettytable
%description cli
This package contains the Chroma CLI which can be used on a Chroma server
or on a separate node.

%package integration-tests
Summary: Intel Manager for Lustre Integration Tests
Group: Development/Tools
Requires: python-requests >= 2.6.0 python-nose python-nose-testconfig python-paramiko python-django python-ordereddict
%description integration-tests
This package contains the Intel Manager for Lustre integration tests and scripts and is intended
to be used by the Chroma test framework.

%package devel
Summary: Contains stripped .py files
Group: Development
Requires: %{name} = %{version}-%{release}
%description devel
This package contains the .py files stripped out of the production build.

%pre
for port in 80 443; do
    if lsof -n -i :$port -s TCP:LISTEN; then
        echo "To install, port $port cannot be bound. Do you have Apache or some other web server running?"
        exit 1
    fi
done

%prep
%setup -n %{name}-%{version}
echo -e "/^DEBUG =/s/= .*$/= False/\nwq" | ed settings.py 2>/dev/null

%build
%{__python} setup.py -q build
# workaround setuptools inanity for top-level datafiles
cp -a chroma-manager.py build/lib
cp -a production_supervisord.conf build/lib
cp -a chroma-manager.conf.template build/lib
cp -a mime.types build/lib
cp -a agent-bootstrap-script.template build/lib

%install
%{__python} setup.py -q install --skip-build --root=%{buildroot}
install -d -p $RPM_BUILD_ROOT%{manager_root}
mv $RPM_BUILD_ROOT/%{python_sitelib}/* $RPM_BUILD_ROOT%{manager_root}
# Do a little dance to get the egg-info in place
mv $RPM_BUILD_ROOT%{manager_root}/*.egg-info $RPM_BUILD_ROOT/%{python_sitelib}
mkdir -p $RPM_BUILD_ROOT/etc/{init,logrotate,nginx/conf}.d
touch $RPM_BUILD_ROOT/etc/nginx/conf.d/chroma-manager.conf
cp %{SOURCE1} $RPM_BUILD_ROOT/etc/init.d/chroma-supervisor
cp %{SOURCE2} $RPM_BUILD_ROOT/etc/init.d/chroma-host-discover
mkdir -p $RPM_BUILD_ROOT/usr/share/man/man1
install %{SOURCE4} $RPM_BUILD_ROOT/usr/share/man/man1
install -m 644 %{SOURCE3} $RPM_BUILD_ROOT/etc/logrotate.d/chroma-manager

# Nuke source code (HYD-1849), but preserve key .py files needed for operation
preserve_patterns="settings.py manage.py chroma_core/migrations/*.py chroma_core/management/commands/*.py"

# Stash .py files for -devel package
find -L $RPM_BUILD_ROOT%{manager_root}/ -name "*.py" \
    | sed -e "s,$RPM_BUILD_ROOT,," > devel.files

# only include compiled modules in the main package
for manager_file in $(find -L $RPM_BUILD_ROOT%{manager_root}/ -name "*.pyc"); do
    install_file=${manager_file/$RPM_BUILD_ROOT\///}
    echo "${install_file%.py*}.py[c,o]" >> manager.files
done

# ... except for these files which are required for operation
for pattern in $preserve_patterns; do
    echo "%{manager_root}/$pattern" >> manager.files
done

# only include compiled modules in the cli package
for cli_file in $(find -L $RPM_BUILD_ROOT%{manager_root}/chroma_cli/ -name "*.pyc"); do
    install_file=${cli_file/$RPM_BUILD_ROOT\///}
    echo "${install_file%.py*}.py[c,o]" >> cli.files
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
%{__python} $RPM_BUILD_ROOT%{manager_root}/scripts/production_nginx.pyc \
    $RPM_BUILD_ROOT%{manager_root}/chroma-manager.conf.template > /etc/nginx/conf.d/chroma-manager.conf

# Create chroma-config MAN Page
makewhatis

# set worker_processes to auto
sed -i '/^worker_processes /s/^/#/' /etc/nginx/nginx.conf
sed -i '1 i\worker_processes auto;' /etc/nginx/nginx.conf

# Start nginx which should present a helpful setup
# page if the user visits it before configuring Chroma fully
%if 0%{?rhel} > 6
    systemctl enable nginx
%else if 0%{?rhel} < 7
    chkconfig nginx on
%endif

# Pre-create log files to set permissions
mkdir -p /var/log/chroma
chown -R nginx:nginx /var/log/chroma

# Only issue SELinux related commands if SELinux is enabled
sestatus| grep enabled &> /dev/null
if [ $(echo $?) == '0' ]; then
    echo "SELinux is enabled!"

    # This is required for opening connections between
    # nginx and rabbitmq-server
    setsebool -P httpd_can_network_connect 1 2>/dev/null

    # This is required because of bad behaviour in python's 'uuid'
    # module (see HYD-1475)
    setsebool -P httpd_tmp_exec 1 2>/dev/null

    # This is required for nginx to serve HTTP_API_PORT
    semanage port -a -t http_port_t -p tcp 8001
else
    echo "SELinux is disabled!"
fi


%if 0%{?rhel} > 6
    if [ $(systemctl is-active firewalld) == "active" ]; then
        for port in 80 443; do
            firewall-cmd --permanent --add-port=$port/tcp
            firewall-cmd --add-port=$port/tcp
        done
    fi
%else if 0%{?rhel} < 7
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
%endif

echo "Thank you for installing Chroma.  To complete your installation, please"
echo "run \"chroma-config setup\""

%preun
service chroma-supervisor stop
# remove the /static/ dir of files that was created by Django's collectstatic
rm -rf %{manager_root}/static

if [ $1 -lt 1 ]; then
    #reset worker processes
    sed -i '/^worker_processes auto;/d' /etc/nginx/nginx.conf
    sed -i '/^#worker_processes /s/^#//' /etc/nginx/nginx.conf
fi

%postun
# Remove chroma-config MAN Page
rm -rf $RPM_BUILD_ROOT/usr/share/man/man1/%{SOURCE4}.gz

if [ $1 -lt 1 ]; then
    %if 0%{?rhel} > 6
        for port in 80 443; do
            firewall-cmd --permanent --remove-port=$port/tcp
            firewall-cmd --remove-port=$port/tcp
        done
        firewall-cmd --permanent --remove-port=123/udp
        firewall-cmd --remove-port=123/udp
    %else if 0%{?rhel} < 7
        # close previously opened ports in the firewall for access to the manager
        sed -i \
            -e '/INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT/d'\
            -e '/INPUT -m state --state NEW -m tcp -p tcp --dport 443 -j ACCEPT/d' \
            -e '/INPUT -m state --state NEW -m udp -p udp --dport 123 -j ACCEPT/d' \
            /etc/sysconfig/iptables
        sed -i -e '/--port=80:tcp/d' -e '/--port=443:tcp/d' \
               -e '/--port=123:udp/d' /etc/sysconfig/system-config-firewall
    %endif

    # clean out /var/lib/chroma
    if [ -d /var/lib/chroma ]; then
        rm -rf /var/lib/chroma
    fi
fi

%files -f manager.files
%defattr(-,root,root)
%{_bindir}/chroma-host-discover
%attr(0700,root,root)%{_bindir}/chroma-config
%dir %attr(0755,nginx,nginx)%{manager_root}
/etc/nginx/conf.d/chroma-manager.conf
%attr(0755,root,root)/etc/init.d/chroma-supervisor
%attr(0755,root,root)/etc/init.d/chroma-host-discover
%attr(0755,root,root)/usr/share/man/man1/chroma-config.1.gz
%attr(0644,root,root)/etc/logrotate.d/chroma-manager
%attr(0755,root,root)%{manager_root}/manage.pyc
%{manager_root}/*.conf
%{manager_root}/agent-bootstrap-script.template
%{manager_root}/chroma-manager.py
%{manager_root}/chroma-manager.conf.template
%{manager_root}/mime.types
%{manager_root}/ui-modules/node_modules/*
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

%files -f cli.files cli
%defattr(-,root,root)
%{_bindir}/chroma

%files integration-tests
%defattr(-,root,root)
%{manager_root}/tests/__init__.pyc
%{manager_root}/tests/utils/*
%{manager_root}/tests/sample_data/*
%{manager_root}/tests/plugins/*
%{manager_root}/tests/integration/*
%{manager_root}/tests/chroma_common/*
%{manager_root}/tests/integration/core/clear_ha_el?.sh
%attr(0755,root,root)%{manager_root}/tests/integration/run_tests

%files -f devel.files devel
%defattr(-,root,root)
