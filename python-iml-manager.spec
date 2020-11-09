%{?systemd_requires}
BuildRequires: systemd

# The install directory for the manager
%{?!manager_root: %global manager_root /usr/share/chroma-manager}
%global pypi_name iml-manager
%global version 6.2.0
%{?!python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

%{?dist_version: %global source https://github.com/whamcloud/%{pypi_name}/archive/%{dist_version}.tar.gz}
%{?dist_version: %global archive_version %{dist_version}}
%{?!dist_version: %global source https://files.pythonhosted.org/packages/source/i/%{pypi_name}/%{pypi_name}-%{version}.tar.gz}
%{?!dist_version: %global archive_version %{version}}

Name:           python-%{pypi_name}
Version:        %{version}
# Release Start
Release:    1%{?dist}
# Release End
Summary:        The Integrated Manager for Lustre Monitoring and Administration Interface
License:        MIT
URL:            https://pypi.python.org/pypi/%{pypi_name}
Source0:        %{source}
Source1:        configuration.tar.gz

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
# Base / EPEL repos
Requires:       createrepo
Requires:       fence-agents
Requires:       fence-agents-virsh
Requires:       ntp
Requires:       pygobject2
Requires:       postgresql96-server >= 9.6.17
Requires:       postgresql96-contrib >= 9.6.17
Requires:       python-daemon
Requires:       python-gunicorn
Requires:       python-networkx
Requires:       python-ordereddict
Requires:       python-paramiko
Requires:       python-psycopg2 = 2.7.7
Requires:       python-setuptools
Requires:       python-requests >= 2.6.0
Requires:       python-uuid
Requires:       python-dateutil >= 1.5
Requires:       python2-jsonschema >= 2.5.1
Requires:       python2-kombu >= 4.2.2
Requires:       python2-mimeparse
Requires:       python2-toolz
Requires:       rabbitmq-server >= 3.3.5-34
Requires:       Django >= 1.11, Django < 1.12
Requires:       policycoreutils-python
Requires:       system-config-firewall-base
Requires:       systemd-python
Requires:       nginx >= 1:1.12.2
Requires:       nodejs >= 1:6.16.0
Requires(post): selinux-policy-targeted
# IML Repo
Requires:       python2-django-tastypie = 0.14.1
Requires:       python2-django-picklefield >= 1.0.0
Requires:       iml-online-help >= 3.1.0
Requires:       iml_sos_plugin >= 2.3.1
Requires:       iml-update-handler >= 1.0.4, iml-update-handler < 2
Requires:       python2-gevent >= 1.0.1
Requires:       python2-httpagentparser >= 1.5
Requires:       python2-iml-manager-libs = %{version}-%{release}
Requires:       python2-requests-unixsocket >= 0.2.0
Requires:       python2-massiviu >= 0.1.0-2
Requires:       rust-iml-action-runner >= 0.4.0
Requires:       rust-iml-agent-comms >= 0.4.0
Requires:       rust-iml-api >= 0.4.0
Requires:       rust-iml-cli >= 0.4.0
Requires:       rust-iml-config-cli >= 0.4.0
Requires:       rust-iml-corosync >= 0.4.0
Requires:       rust-iml-device >= 0.4.0
Requires:       rust-iml-gui >= 0.3.0
Requires:       rust-iml-journal >= 0.4.0
Requires:       rust-iml-mailbox >= 0.4.0
Requires:       rust-iml-network >= 0.4.0
Requires:       rust-iml-ntp >= 0.4.0
Requires:       rust-iml-ostpool >= 0.4.0
Requires:       rust-iml-postoffice >= 0.4.0
Requires:       rust-iml-report >= 0.4.0
Requires:       rust-iml-sfa >= 0.4.0
Requires:       rust-iml-snapshot >= 0.4.0
Requires:       rust-iml-stats >= 0.4.0
Requires:       rust-iml-task-runner >= 0.4.0
Requires:       rust-iml-warp-drive >= 0.4.0
Requires:       rust-iml-timer >= 0.4.0
# Other Repos
Requires:       influxdb
Requires:       grafana

Conflicts:      chroma-agent
Obsoletes:      chroma-manager
Provides:       chroma-manager
Obsoletes:      Django-south
Obsoletes:      django-celery
Obsoletes:      django-picklefield
Obsoletes:      django-tastypie
Obsoletes:      python2-django16
Obsoletes:      python2-dse
Obsoletes:      python2-iml-manager-cli

%{?python_provide:%python_provide python2-%{pypi_name}}

%description -n python2-%{pypi_name}
This is the Integrated Manager for Lustre Monitoring and Administration Interface

%package -n     python2-%{pypi_name}-libs
Summary:        Common libraries for Chroma Server
Group:          System/Libraries
Requires:       python2-iml-common1.4 >= 1.4.5
Obsoletes:      chroma-manager-libs
Provides:       chroma-manager-libs

%description -n     python2-%{pypi_name}-libs
This package contains libraries for Chroma CLI and Chroma Server.


%package -n     python2-%{pypi_name}-integration-tests
Summary: Integrated Manager for Lustre Integration Tests
Group: Development/Tools
Requires: python-requests >= 2.6.0 python-nose python-nose-testconfig python-paramiko python-ordereddict python2-iml-common1.4 python-packaging
Requires: Django >= 1.11, Django < 1.12
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
%setup -T -D -a 1 -n %{pypi_name}-%(echo %{archive_version} | sed -Ee '/^v([0-9]+\.)[0-9]+/s/^v(.*)/\1/')
%else
%setup -n %{pypi_name}-%{version}
%setup -T -D -a 1 -n %{pypi_name}-%{version}
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
gzip -9 chroma-config.1

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
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/grafana/provisioning/dashboards
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/grafana/provisioning/datasources
cp -r grafana $RPM_BUILD_ROOT%{manager_root}
mv $RPM_BUILD_ROOT%{manager_root}/grafana/grafana-iml.ini $RPM_BUILD_ROOT%{_sysconfdir}/grafana/
mv $RPM_BUILD_ROOT%{manager_root}/grafana/dashboards/iml-dashboards.yaml $RPM_BUILD_ROOT%{_sysconfdir}/grafana/provisioning/dashboards
mv $RPM_BUILD_ROOT%{manager_root}/grafana/datasources/influxdb-iml-datasource.yml $RPM_BUILD_ROOT%{_sysconfdir}/grafana/provisioning/datasources
mkdir -p $RPM_BUILD_ROOT%{_unitdir}/grafana-server.service.d/
mv $RPM_BUILD_ROOT%{manager_root}/grafana/dropin-iml.conf $RPM_BUILD_ROOT%{_unitdir}/grafana-server.service.d/90-iml.conf
cp -r nginx $RPM_BUILD_ROOT%{manager_root}
mkdir -p $RPM_BUILD_ROOT%{_unitdir}/nginx.service.d/
mv $RPM_BUILD_ROOT%{manager_root}/nginx/nginx-dropin-iml.conf $RPM_BUILD_ROOT%{_unitdir}/nginx.service.d/90-nginx-dropin-iml.conf
mkdir -p $RPM_BUILD_ROOT%{_unitdir}/rabbitmq-server.service.d
mv rabbitmq-server-dropin.conf $RPM_BUILD_ROOT%{_unitdir}/rabbitmq-server.service.d/90-rabbitmq-server-dropin.conf
cp iml-manager-redirect.conf $RPM_BUILD_ROOT%{_sysconfdir}/nginx/default.d/iml-manager-redirect.conf
cp rabbitmq-env.conf $RPM_BUILD_ROOT%{_sysconfdir}/rabbitmq/rabbitmq-env.conf
mkdir -p $RPM_BUILD_ROOT%{_mandir}/man1
install chroma-config.1.gz $RPM_BUILD_ROOT%{_mandir}/man1
install -m 644 logrotate.cfg $RPM_BUILD_ROOT%{_sysconfdir}/logrotate.d/chroma-manager
mkdir -p $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 iml-manager.target $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 iml-corosync.service $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 iml-gunicorn.service $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 iml-http-agent.service $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 iml-job-scheduler.service $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 iml-lustre-audit.service $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 iml-plugin-runner.service $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 iml-power-control.service $RPM_BUILD_ROOT%{_unitdir}/
install -m 644 iml-settings-populator.service $RPM_BUILD_ROOT%{_unitdir}/
mkdir -p $RPM_BUILD_ROOT/var/log/chroma

# only include modules in the main package
for manager_file in $(find -L $RPM_BUILD_ROOT%{manager_root}/ -name "*.py"); do
    install_file=${manager_file/$RPM_BUILD_ROOT\///}
    echo "${install_file%.py*}.py*" >> manager.files
done

# This is fugly, but it's cleaner than moving things around to get our
# modules in the standard path.
ed $RPM_BUILD_ROOT/usr/bin/chroma-config <<EOF
/import load_entry_point/ a
sys.path.insert(0, "%{manager_root}")
.
w
q
EOF

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

%posttrans -n python2-%{pypi_name}-libs
rmdir %{python_sitelib}/iml_manager-5.0.*.egg-info 2> /dev/null || :

%preun -n python2-%{pypi_name}
%systemd_preun iml-manager.target
%systemd_preun iml-corosync.service
%systemd_preun iml-gunicorn.service
%systemd_preun iml-http-agent.service
%systemd_preun iml-job-scheduler.service
%systemd_preun iml-lustre-audit.service
%systemd_preun iml-plugin-runner.service
%systemd_preun iml-power-control.service
%systemd_preun iml-settings-populator.service
%systemd_preun iml-syslog.service
%systemd_preun iml-warp-drive.service

%postun -n python2-%{pypi_name}
if [ $1 -lt 1 ]; then
    for port in 80 443; do
        firewall-cmd --permanent --remove-port=$port/tcp
        firewall-cmd --remove-port=$port/tcp
    done
    firewall-cmd --permanent --remove-port=123/udp
    firewall-cmd --remove-port=123/udp
fi

%files -f manager.files -n python2-%{pypi_name}
%defattr(-,root,root)
%attr(0700,root,root)%{_bindir}/chroma-config
%dir %attr(0755,nginx,nginx)%{manager_root}
%dir %attr(0755,nginx,nginx)/var/log/chroma
%ghost %{_sysconfdir}/nginx/conf.d/chroma-manager.conf
%{_sysconfdir}/nginx/default.d/iml-manager-redirect.conf
%{_sysconfdir}/rabbitmq/rabbitmq-env.conf
%{_sysconfdir}/grafana/grafana-iml.ini
%{_unitdir}/grafana-server.service.d/90-iml.conf
%{_unitdir}/rabbitmq-server.service.d/90-rabbitmq-server-dropin.conf
%{_unitdir}/nginx.service.d/90-nginx-dropin-iml.conf
%attr(0755,root,root)%{_mandir}/man1/chroma-config.1.gz
%attr(0644,root,root)%{_sysconfdir}/logrotate.d/chroma-manager
%attr(0644,root,grafana)%{_sysconfdir}/grafana/provisioning/dashboards/iml-dashboards.yaml
%attr(0674,root,grafana)%{manager_root}/grafana/dashboards/
%attr(0644,root,grafana)%{_sysconfdir}/grafana/provisioning/datasources/influxdb-iml-datasource.yml
%attr(0644,root,root)%{_unitdir}/iml-manager.target
%attr(0644,root,root)%{_unitdir}/*.service
%attr(0755,root,root)%{manager_root}/manage.py
%{manager_root}/agent-bootstrap-script.template
%{manager_root}/chroma-manager.conf.template
%{manager_root}/chroma_core/fixtures/
%{manager_root}/polymorphic/COPYING
%config(noreplace) %{manager_root}/*.repo
%{manager_root}/*.profile

# Stuff below goes into the -cli/-lib packages
%exclude %{python_sitelib}/*.egg-info/
# will go into the -tests packages
%exclude %{manager_root}/example_storage_plugin_package
%exclude %{manager_root}/tests
%doc licenses/*

%files -n python2-%{pypi_name}-libs
%{python_sitelib}/*.egg-info/
