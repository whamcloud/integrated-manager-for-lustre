%{!?name: %define name chroma-agent}
%{?!version: %define version %(%{__python} -c "from chroma_agent import version; sys.stdout.write(version())")}
%{?!package_release: %define package_release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: Chroma Agent
Name: %{name}
Version: %{version}
Release: %{package_release}%{?dist}
Source0: %{name}-%{version}.tar.gz
Source1: chroma-agent-init.sh
Source2: lustre-modules-init.sh
Source3: logrotate.cfg
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Intel Corporation <hpdd-info@intel.com>
Url: http://lustre.intel.com/
BuildRequires: python-setuptools
Requires: ntp
Requires: python-argparse
Requires: python-daemon
Requires: python-setuptools
Requires: python-requests >= 2.6.0
Requires: python-tablib yum-utils
Requires: initscripts
Requires: chroma-diagnostics >= %{version}
%if 0%{?rhel} > 5
Requires: util-linux-ng
%endif
Requires(post): selinux-policy

%description
This is the Intel Manager for Lustre monitoring and adminstration agent

%package management
Summary: Management functionality layer.
Group: System/Utility
Conflicts: sysklogd

Requires: %{name} = %{version}-%{release}
Requires: rsyslog
Requires: pcs
Requires: libxml2-python
Requires: python-netaddr
Requires: python-ethtool
Requires: python-jinja2
Requires: pcapy
Requires: python-impacket
Requires: system-config-firewall-base
Requires: ed

%if 0%{?rhel} < 7
Obsoletes: pacemaker-iml <= 1.1.12-4.wc1.el6
Obsoletes: pacemaker-iml-cluster-libs <= 1.1.12-4.wc1.el6
Obsoletes: pacemaker-iml-libs <= 1.1.12-4.wc1.el6
Obsoletes: pacemaker-iml-cli <= 1.1.12-4.wc1.el6
Requires: pacemaker-iml = 1.1.12-4.wc2.el6
Requires: fence-agents-iml >= 3.1.5-48.wc1.el6.2
%endif

%if 0%{?rhel} > 6
Requires: fence-agents
Requires: fence-agents-virsh
%endif

%description management
This package layers on management capabilities for Intel Manager for Lustre Agent.

%package devel
Summary: Contains stripped .py files
Group: Development
Requires: %{name} = %{version}-%{release}
%description devel
This package contains the .py files stripped out of the production build.

%prep
%setup -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --install-lib=%{python_sitelib} --install-scripts=%{_bindir} --root=%{buildroot}
mkdir -p $RPM_BUILD_ROOT/usr/sbin/
mv $RPM_BUILD_ROOT/usr/{,s}bin/fence_chroma
mv $RPM_BUILD_ROOT/usr/{,s}bin/chroma-copytool-monitor
mkdir -p $RPM_BUILD_ROOT/etc/{init,logrotate}.d/
cp %{SOURCE1} $RPM_BUILD_ROOT/etc/init.d/chroma-agent
cp %{SOURCE2} $RPM_BUILD_ROOT/etc/init.d/lustre-modules
install -m 644 %{SOURCE3} $RPM_BUILD_ROOT/etc/logrotate.d/chroma-agent

# Nuke source code (HYD-1849)
find -L $RPM_BUILD_ROOT%{python_sitelib}/chroma_agent -name "*.py" | sed -e "s,$RPM_BUILD_ROOT,," > devel.files

touch management.files
cat <<EndOfList>>management.files
%{python_sitelib}/chroma_agent/action_plugins/manage_*.py[c,o]
%{python_sitelib}/chroma_agent/templates/
/usr/lib/ocf/resource.d/chroma/Target
%{_sbindir}/fence_chroma
%{_sbindir}/chroma-copytool-monitor
EndOfList

touch base.files
for base_file in $(find -L $RPM_BUILD_ROOT -type f -name '*.pyc'); do
  install_file=${base_file/$RPM_BUILD_ROOT\///}
  for mgmt_pat in $(<management.files); do
    if [[ $install_file == $mgmt_pat ]]; then
      continue 2
    fi
  done
  echo "${install_file%.py*}.py[c,o]" >> base.files
done

%clean
rm -rf %{buildroot}

%post
chkconfig lustre-modules on
# disable SELinux -- it prevents both lustre and pacemaker from working
sed -ie 's/^SELINUX=.*$/SELINUX=disabled/' /etc/selinux/config
# the above only disables on the next boot.  disable it currently, also
echo 0 > /selinux/enforce

if [ $1 -eq 1 ]; then
    # new install; create default agent config
    chroma-agent reset_agent_config
elif [ $1 -eq 2 ]; then
    # upgrade; convert any older agent config
    chroma-agent convert_agent_config
fi

%post management
chkconfig rsyslog on

# when a kernel is installed, make sure that our kernel is reset back to
# being the preferred boot kernel
%triggerin management -- kernel
MOST_RECENT_KERNEL_VERSION=$(rpm -q kernel --qf "%{INSTALLTIME} %{VERSION}-%{RELEASE}.%{ARCH}\n" | sort -nr | sed -n -e '/_lustre/{s/.* //p;q}')
grubby --set-default=/boot/vmlinuz-$MOST_RECENT_KERNEL_VERSION

%files -f base.files
%defattr(-,root,root)
%attr(0755,root,root)/etc/init.d/chroma-agent
%attr(0755,root,root)/etc/init.d/lustre-modules
%{_bindir}/chroma-agent*
%{python_sitelib}/chroma_agent-*.egg-info/*
%attr(0644,root,root)/etc/logrotate.d/chroma-agent

%files -f management.files management
%defattr(-,root,root)

%files -f devel.files devel
%defattr(-,root,root)
