%{?systemd_requires}
BuildRequires: systemd

%define unit_name chroma-agent.service

%global pypi_name iml-agent
%{?!version: %global version 5.2.0}
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
Summary:        IML Agent
License:        MIT
URL:            https://pypi.python.org/pypi/%{pypi_name}
Source0:        %{source}
Group:          Development/Libraries
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix:         %{_prefix}
BuildArch:      noarch
Vendor:         Whamcloud <iml@whamcloud.com>
BuildRequires:  python2-setuptools
BuildRequires:  systemd

%description
This is the Integrated Manager for Lustre monitoring and adminstration agent

%package -n     python2-%{pypi_name}
Summary:        %{summary}
Obsoletes:      chroma-agent
Provides:       chroma-agent
Requires:       ntp
Requires:       python-argparse
Requires:       python-daemon
Requires:       python-setuptools
Requires:       python-requests >= 2.6.0
Requires:       yum-utils
Requires:       emf-sos-plugin >= 2.4.0
Requires:       python2-iml-common1.4 >= 1.4.5
Requires:       python2-toolz
Requires:       iml-device-scanner >= 4.0.0
Requires:       util-linux-ng
Requires(post): selinux-policy
Requires:       python-urllib3
%{?python_provide:%python_provide python2-%{pypi_name}}

%description -n python2-%{pypi_name}
This is the Integrated Manager for Lustre monitoring and adminstration agent

%package -n     python2-%{pypi_name}-management
Summary:        Management functionality layer.
Group:          System Environment/Daemons
Conflicts:      sysklogd
Obsoletes:      chroma-agent-management
Provides:       chroma-agent-management

Requires:       python2-%{pypi_name} = %{version}-%{release}
Requires:       libxml2-python
Requires:       python-netaddr
Requires:       python-ethtool
Requires:       python-jinja2
Requires:       python2-scapy
Requires:       system-config-firewall-base
Requires:       ed

%description -n python2-%{pypi_name}-management
This package layers on management capabilities for Integrated Manager for Lustre Agent.

If using with pacemaker: pcs, fencing and resource agents should be installed.
RPMS: pcs fence-agents lustre-resource-agents

%prep
%if %{?dist_version:1}%{!?dist_version:0}
%setup -n %{pypi_name}-%(echo %{archive_version} | sed -Ee '/^v([0-9]+\.)[0-9]+/s/^v(.*)/\1/')
%else
%setup -n %{pypi_name}-%{version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info
%endif

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --install-lib=%{python_sitelib} --install-scripts=%{_bindir} --root=%{buildroot}
mkdir -p $RPM_BUILD_ROOT/usr/sbin/
mv $RPM_BUILD_ROOT/usr/{,s}bin/fence_chroma
mv $RPM_BUILD_ROOT/usr/{,s}bin/chroma-copytool-monitor
mkdir -p %{buildroot}%{_unitdir}/device-scanner.target.d/
install -m 644 %{unit_name} %{buildroot}%{_unitdir}/
install -m 644 iml-storage-server.target %{buildroot}%{_unitdir}/iml-storage-server.target
install -m 644 10-device-scanner.target.conf %{buildroot}%{_unitdir}/device-scanner.target.d/10-device-scanner.target.conf
mkdir -p %{buildroot}%{_presetdir}
install -m 644 50-chroma-agent.preset %{buildroot}%{_presetdir}/
mkdir -p $RPM_BUILD_ROOT/etc/{init,logrotate}.d/
install -m 644 logrotate.cfg $RPM_BUILD_ROOT/etc/logrotate.d/chroma-agent
mkdir -p %{buildroot}%{_unitdir}/device-scanner.target.d/

touch management.files
cat <<EndOfList>>management.files
%{python_sitelib}/chroma_agent/action_plugins/manage_*.py*
%{python_sitelib}/chroma_agent/templates/
%{_sbindir}/fence_chroma
%{_sbindir}/chroma-copytool-monitor
EndOfList

touch base.files
for base_file in $(find -L $RPM_BUILD_ROOT -type f -name '*.py'); do
  install_file=${base_file/$RPM_BUILD_ROOT\///}
  for mgmt_pat in $(<management.files); do
    if [[ $install_file == $mgmt_pat ]]; then
      continue 2
    fi
  done
  echo "${install_file%.py*}.py*" >> base.files
done

%clean
rm -rf %{buildroot}

%post -n python2-%{pypi_name}
# disable SELinux -- it prevents both lustre and pacemaker from working
sed -ie 's/^SELINUX=.*$/SELINUX=disabled/' /etc/selinux/config
# the above only disables on the next boot.  set to permissive currently, also
setenforce 0

%systemd_post iml-storage-server.target
%systemd_post %{unit_name}

# this will either convert an old (pre-4.1) config or initialize
chroma-agent convert_agent_config >/dev/null 2>&1 || :

%preun
%systemd_preun %{unit_name}

%triggerin -n python2-%{pypi_name}-management -- kernel
# when a kernel is installed, make sure that our kernel is reset back to
# being the preferred boot kernel
MOST_RECENT_KERNEL_VERSION=$(rpm -q kernel --qf "%{INSTALLTIME} %{VERSION}-%{RELEASE}.%{ARCH}\n" | sort -nr | sed -n -e '/_lustre/{s/.* //p;q}')
grubby --set-default=/boot/vmlinuz-$MOST_RECENT_KERNEL_VERSION

%files -f base.files -n python2-%{pypi_name}
%defattr(-,root,root)
%attr(0644,root,root)%{_unitdir}/%{unit_name}
%attr(0644,root,root)%{_presetdir}/50-chroma-agent.preset
%attr(0644,root,root)%{_unitdir}/iml-storage-server.target
%attr(0644,root,root)%{_unitdir}/device-scanner.target.d/10-device-scanner.target.conf
%{_bindir}/chroma-agent*
%{python_sitelib}/%(a=%{pypi_name}; echo ${a//-/_})-*.egg-info/*
%attr(0644,root,root)/etc/logrotate.d/chroma-agent

%files -f management.files -n python2-%{pypi_name}-management
%defattr(-,root,root)

%changelog
* Mon Oct 14 2019 Joe Grund <jgrund@whamcloud.com> - 4.2.0-1
- Pin mimimum IML version requirements

* Mon Jan 7 2019 Joe Grund <jgrund@whamcloud.com> - 4.1.2.0-1
- Use Docker copr image instead of module-tools

* Mon Jul 16 2018 Joe Grund <jgrund@whamcloud.com> - 4.1.1.0-1
- Remove old package update scan from this project.

* Fri Dec 1 2017 Brian J. Murrell <brian.murrell@intel.com> - 4.0.5.0-1
- Initial module
  * split out from the intel-manager-for-lustre project

