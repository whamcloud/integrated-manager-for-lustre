%{?systemd_requires}
BuildRequires: systemd

# The install directory for the manager
%{?!manager_root: %global manager_root /usr/share/chroma-manager}
%global pypi_name iml-manager
%global version 5.0.0
%{?!python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

%{?dist_version: %global source https://github.com/whamcloud/%{pypi_name}/archive/%{dist_version}.tar.gz}
%{?dist_version: %global archive_version %{dist_version}}
%{?!dist_version: %global source https://files.pythonhosted.org/packages/source/i/%{pypi_name}/%{pypi_name}-%{version}.tar.gz}
%{?!dist_version: %global archive_version %{version}}

Name:           python-%{pypi_name}
Version:        %{version}
# Release Start
Release:    7%{?dist}
# Release End
Summary:        The Integrated Manager for Lustre Monitoring and Administration Interface
License:        MIT
URL:            https://pypi.python.org/pypi/%{pypi_name}
Source0:        %{source}
Source1:        chroma-host-discover-init.sh
Source2:        logrotate.cfg
Source3:        chroma-config.1
Source4:        iml-corosync.service
Source5:        iml-gunicorn.service
Source6:        iml-http-agent.service
Source7:        iml-job-scheduler.service
Source8:        iml-lustre-audit.service
Source9:        iml-manager.target
Source10:       iml-plugin-runner.service
Source11:       iml-power-control.service
Source12:       iml-settings-populator.service
Source13:       iml-stats.service
Source14:       iml-syslog.service
Source16:       iml-manager-redirect.conf
Source17:       rabbitmq-env.conf
Source18:	grafana-iml.ini

Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch:      noarch
Vendor: whamCloud <iml@whamcloud.com>
BuildRequires: python2-setuptools
BuildRequires: ed

%description
This is the Integrated Manager for Lustre Monitoring and Administration Interface

%package -n     python2-%{pypi_name}
Summary:        %{summary}
Requires:       python-setuptools
Requires:       python-prettytable
Requires:       python-massiviu >= 0.1.0-2
Requires:       python2-jsonschema >= 2.5.1
Requires:       python-ordereddict
Requires:       python-uuid
Requires:       python-paramiko
Requires:       python2-kombu >= 3.0.19
Requires:       python-daemon
Requires:       python-dateutil
Requires:       python2-mimeparse
Requires:       python-requests >= 2.6.0
Requires:       python-networkx
Requires:       python2-httpagentparser
Requires:       python-gunicorn
Requires:       pygobject2
Requires:       postgresql-server
Requires:       python-psycopg2
Requires:       rabbitmq-server >= 3.3.5-34
Requires:       ntp
Requires:       Django >= 1.6, Django < 1.7
Requires:       Django-south >= 1.0.2
Requires:       python2-django-tastypie = 0.12.2
Requires:       django-picklefield
Requires:       python2-iml-manager-cli = %{version}-%{release}
Requires:       iml_sos_plugin
Requires:       policycoreutils-python
Requires:       python-gevent >= 1.0.1
Requires:       system-config-firewall-base
Requires:       nodejs >= 1:6.9.4-2
Requires:       iml-gui >= 6.4.0
Requires:       iml-old-gui
Requires:       iml-srcmap-reverse >= 3.0.7
Requires:       iml-online-help
Requires:       iml-device-scanner-aggregator
Requires:       iml-realtime
Requires:       iml-view-server
Requires:       iml-socket-worker
Requires:       python2-requests-unixsocket
Requires:       rust-iml-warp-drive
Requires:       rust-iml-action-runner
Requires:       rust-iml-agent-comms
Requires:       rust-iml-stratagem
Requires:       rust-iml-mailbox
Requires:       createrepo
Requires:       python2-toolz
Requires:       iml-update-handler < 2
Requires:       iml-wasm-components
Conflicts:      chroma-agent
Requires(post): selinux-policy-targeted
Obsoletes:      chroma-manager
Provides:       chroma-manager
Obsoletes:      nodejs-active-x-obfuscator
Obsoletes:      nodejs-bunyan
Obsoletes:      nodejs-commander
Obsoletes:      nodejs-nan
Obsoletes:      nodejs-primus
Obsoletes:      nodejs-primus-emitter
Obsoletes:      nodejs-primus-multiplex
Obsoletes:      nodejs-request
Obsoletes:      nodejs-socket.io
Obsoletes:      nodejs-socket.io-client
Obsoletes:      nodejs-ws
Obsoletes:      nodejs-tinycolor
Obsoletes:      nodejs-extendable
Obsoletes:      nodejs-xmlhttprequest
Obsoletes:      nodejs-dotty
Obsoletes:      nodejs-tough-cookie
Obsoletes:      nodejs-options
Obsoletes:      nodejs-punycode
Obsoletes:      nodejs-load
Obsoletes:      nodejs-json-stringify-safe
Obsoletes:      nodejs-lodash
Obsoletes:      nodejs-moment
Obsoletes:      nodejs-q
Obsoletes:      nodejs-qs
Obsoletes:      nodejs-node-uuid
Obsoletes:      nodejs-mime
Obsoletes:      nodejs-base64id
Obsoletes:      nodejs-policyfile
Obsoletes:      nodejs-uritemplate
Obsoletes:      nodejs-forever-agent
Obsoletes:      nodejs-uglify-js
Obsoletes:      nodejs-di
Obsoletes:      nodejs-mv
Obsoletes:      nodejs-json-mask
Obsoletes:      nodejs-zeparser
Obsoletes:      django-celery
Obsoletes:      django-tastypie
Obsoletes:      python2-dse
Obsoletes:      Django-south

Requires:      fence-agents
Requires:      fence-agents-virsh
Requires:      nginx >= 1:1.11.6
Requires:      influxdb
Requires:	grafana
%{?python_provide:%python_provide python2-%{pypi_name}}

%description -n python2-%{pypi_name}
This is the Integrated Manager for Lustre Monitoring and Administration Interface

%package -n     python2-%{pypi_name}-libs
Summary:        Common libraries for Chroma Server
Group:          System/Libraries
Requires:       python2-iml-common1.4
Obsoletes:      chroma-manager-libs
Provides:       chroma-manager-libs

%description -n     python2-%{pypi_name}-libs
This package contains libraries for Chroma CLI and Chroma Server.

%package -n     python2-%{pypi_name}-cli
Summary: Command-Line Interface for Chroma Server
Group: System/Utility
Requires: python2-iml-manager-libs = %{version}-%{release} python-argparse python-requests >= 2.6.0 python-tablib python-prettytable
Obsoletes: chroma-manager-cli
Provides: chroma-manager-cli

%description -n     python2-%{pypi_name}-cli
This package contains the Chroma CLI which can be used on a Chroma server
or on a separate node.

%package -n     python2-%{pypi_name}-integration-tests
Summary: Integrated Manager for Lustre Integration Tests
Group: Development/Tools
Requires: python-requests >= 2.6.0 python-nose python-nose-testconfig python-paramiko python-ordereddict python2-iml-common1.4 python-packaging
Requires: Django >= 1.6, Django < 1.7
%description -n     python2-%{pypi_name}-integration-tests
This package contains the Integrated Manager for Lustre integration tests and scripts and is intended
to be used by the Chroma test framework.

%pre
for port in 80 443; do
    if lsof -n -i :$port -s TCP:LISTEN; then
        echo "To install, port $port cannot be bound. Do you have Apache or some other web server running?"
        exit 1
    fi
done

%prep
%if %{?dist_version:1}%{!?dist_version:0}
%setup -n %{pypi_name}-%(echo %{archive_version} | sed -Ee '/^v([0-9]+\.)[0-9]+/s/^v(.*)/\1/')
%else
%setup -n %{pypi_name}-%{version}
%endif
echo -e "/^DEBUG =/s/= .*$/= False/\nwq" | ed settings.py 2>/dev/null

%build
%{__python} setup.py build
# workaround setuptools inanity for top-level datafiles
cp -a wsgi.py build/lib
cp -a chroma-manager.conf.template build/lib
cp -a agent-bootstrap-script.template build/lib
cp -a *.profile build/lib
cp -a *.repo build/lib
gzip -9 %{SOURCE3}

%install
%{__python} setup.py -q install --skip-build --root=%{buildroot}
install -d -p $RPM_BUILD_ROOT%{manager_root}
mv $RPM_BUILD_ROOT/%{python_sitelib}/* $RPM_BUILD_ROOT%{manager_root}
# Do a little dance to get the egg-info in place
mv $RPM_BUILD_ROOT%{manager_root}/*.egg-info $RPM_BUILD_ROOT/%{python_sitelib}
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/{init,logrotate,nginx/conf,nginx/default}.d
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/rabbitmq
touch $RPM_BUILD_ROOT%{_sysconfdir}/nginx/conf.d/chroma-manager.conf
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/rabbitmq
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/grafana
install -m 644 %{SOURCE18} $RPM_BUILD_ROOT%{_sysconfdir}/grafana/
cp %{SOURCE16} $RPM_BUILD_ROOT%{_sysconfdir}/nginx/default.d/iml-manager-redirect.conf
cp %{SOURCE17} $RPM_BUILD_ROOT%{_sysconfdir}/rabbitmq/rabbitmq-env.conf
cp %{SOURCE1} $RPM_BUILD_ROOT%{_sysconfdir}/init.d/chroma-host-discover
mkdir -p $RPM_BUILD_ROOT%{_mandir}/man1
install %{SOURCE3}.gz $RPM_BUILD_ROOT%{_mandir}/man1
install -m 644 %{SOURCE2} $RPM_BUILD_ROOT%{_sysconfdir}/logrotate.d/chroma-manager
mkdir -p $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE4} $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE5} $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE6} $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE7} $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE8} $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE9} $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE10} $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE11} $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE12} $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE13} $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 %{SOURCE14} $RPM_BUILD_ROOT%{_unitdir}/
mkdir -p $RPM_BUILD_ROOT/var/log/chroma

# only include modules in the main package
for manager_file in $(find -L $RPM_BUILD_ROOT%{manager_root}/ -name "*.py"); do
    install_file=${manager_file/$RPM_BUILD_ROOT\///}
    echo "${install_file%.py*}.py*" >> manager.files
done

# only include modules in the cli package
for cli_file in $(find -L $RPM_BUILD_ROOT%{manager_root}/chroma_cli/ -name "*.py"); do
    install_file=${cli_file/$RPM_BUILD_ROOT\///}
    echo "${install_file%.py*}.py*" >> cli.files
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

%post -n python2-%{pypi_name}
if [ $1 -eq 1 ]; then
    systemctl enable nginx

    echo "Thank you for installing IML. To complete your installation, please"
    echo "run \"chroma-config setup\""
fi

if [ $1 -gt 1 ]; then
    systemctl reload nginx

    echo "Thank you for updating IML. To complete your upgrade, please"
    echo "run \"chroma-config setup\""
fi

%posttrans -n python2-%{pypi_name}
if [ -d %{_localstatedir}/lib/rpm-state/%{name}/ ]; then
    mkdir -p /var/lib/chroma/
    cp -rf %{_localstatedir}/lib/rpm-state/%{name}/* /var/lib/chroma/
    rm -rf %{_localstatedir}/lib/rpm-state/%{name}/
    rm -rf /var/lib/chroma/repo/iml-agent
fi

%triggerun -n python2-%{pypi_name} -- chroma-manager
mkdir -p %{_localstatedir}/lib/rpm-state/%{name}/
cp -r /var/lib/chroma/* %{_localstatedir}/lib/rpm-state/%{name}/

%preun -n python2-%{pypi_name}
%systemd_preun iml-manager.target
%systemd_preun iml-corosync.service
%systemd_preun iml-gunicorn.service
%systemd_preun iml-http-agent.service
%systemd_preun iml-job-scheduler.service
%systemd_preun iml-lustre-audit.service
%systemd_preun iml-plugin-runner.service
%systemd_preun iml-power-control.service
%systemd_preun iml-realtime.service
%systemd_preun iml-settings-populator.service
%systemd_preun iml-stats.service
%systemd_preun iml-syslog.service
%systemd_preun iml-view-server.service
%systemd_preun iml-warp-drive.service

%postun -n python2-%{pypi_name}
if [ $1 -lt 1 ]; then
    for port in 80 443; do
        firewall-cmd --permanent --remove-port=$port/tcp
        firewall-cmd --remove-port=$port/tcp
    done
    firewall-cmd --permanent --remove-port=123/udp
    firewall-cmd --remove-port=123/udp

    # clean out /var/lib/chroma
    if [ -d /var/lib/chroma ]; then
        rm -rf /var/lib/chroma
    fi
fi

%files -f manager.files -n python2-%{pypi_name}
%defattr(-,root,root)
%{_bindir}/chroma-host-discover
%attr(0700,root,root)%{_bindir}/chroma-config
%dir %attr(0755,nginx,nginx)%{manager_root}
%dir %attr(0755,nginx,nginx)/var/log/chroma
%ghost %{_sysconfdir}/nginx/conf.d/chroma-manager.conf
%{_sysconfdir}/nginx/default.d/iml-manager-redirect.conf
%{_sysconfdir}/rabbitmq/rabbitmq-env.conf
%{_sysconfdir}/grafana/grafana-iml.ini
%attr(0755,root,root)%{_sysconfdir}/init.d/chroma-host-discover
%attr(0755,root,root)%{_mandir}/man1/chroma-config.1.gz
%attr(0644,root,root)%{_sysconfdir}/logrotate.d/chroma-manager
%attr(0644,root,root)%{_unitdir}/iml-corosync.service
%attr(0644,root,root)%{_unitdir}/iml-gunicorn.service
%attr(0644,root,root)%{_unitdir}/iml-http-agent.service
%attr(0644,root,root)%{_unitdir}/iml-job-scheduler.service
%attr(0644,root,root)%{_unitdir}/iml-lustre-audit.service
%attr(0644,root,root)%{_unitdir}/iml-manager.target
%attr(0644,root,root)%{_unitdir}/iml-plugin-runner.service
%attr(0644,root,root)%{_unitdir}/iml-power-control.service
%attr(0644,root,root)%{_unitdir}/iml-settings-populator.service
%attr(0644,root,root)%{_unitdir}/iml-stats.service
%attr(0644,root,root)%{_unitdir}/iml-syslog.service
%attr(0755,root,root)%{manager_root}/manage.py
%{manager_root}/agent-bootstrap-script.template
%{manager_root}/chroma-manager.conf.template
%{manager_root}/chroma_core/fixtures/*
%{manager_root}/polymorphic/COPYING
%config(noreplace) %{manager_root}/*.repo
%{manager_root}/*.profile

# Stuff below goes into the -cli/-lib packages
%exclude %{manager_root}/chroma_cli
%exclude %{python_sitelib}/*.egg-info/
# will go into the -tests packages
%exclude %{manager_root}/example_storage_plugin_package
%exclude %{manager_root}/tests
%doc licenses/*

%files -n python2-%{pypi_name}-libs
%{python_sitelib}/*.egg-info/*

%files -f cli.files -n python2-%{pypi_name}-cli
%defattr(-,root,root)
%{_bindir}/chroma

%files -n python2-%{pypi_name}-integration-tests
%defattr(-,root,root)
%{manager_root}/tests/__init__.py
%{manager_root}/tests/utils/*
%{manager_root}/tests/sample_data/*
%{manager_root}/tests/plugins/*
%{manager_root}/tests/integration/*
