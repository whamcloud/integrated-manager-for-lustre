%{!?name: %define name chroma-agent}
%{?!version: %define version %(%{__python} -c "from chroma_agent import version; sys.stdout.write(version())")}
%{?!release: %define release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: Chroma Agent
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
Source1: chroma-agent-init.sh
Source2: lustre-modules-init.sh
Source3: logrotate.cfg
Source4: copytool.conf
Source5: copytool-monitor.conf
Source6: start-copytools.conf
Source7: start-copytool-monitors.conf
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Intel Corporation <hpdd-info@intel.com>
Url: http://lustre.intel.com/
BuildRequires: python-setuptools
Requires: ntp python-simplejson python-argparse python-daemon python-setuptools python-requests >= 1.0.3 python-tablib yum-utils
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
Obsoletes: pacemaker-iml <= 1.1.7-6.wc2.el6 pacemaker-iml-cluster-libs <= 1.1.7-6.wc2.el6 pacemaker-iml-libs <= 1.1.7-6.wc2.el6 pacemaker-iml-cli <= 1.1.7-6.wc2.el6
Requires: %{name} = %{version}-%{release} rsyslog pcs pacemaker > 1.1.7-6.wc2.el6 python-dateutil >= 1.5 libxml2-python python-netaddr python-ethtool python-jinja2 pcapy python-impacket system-config-firewall-base ed at
Requires: fence-agents-iml >= 3.1.5-48.wc1.el6.3
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
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/init
cp %{SOURCE4} %{SOURCE5} %{SOURCE6} %{SOURCE7} $RPM_BUILD_ROOT%{_sysconfdir}/init

# Nuke source code (HYD-1849)
find -L $RPM_BUILD_ROOT%{python_sitelib}/chroma_agent -name "*.py" | sed -e "s,$RPM_BUILD_ROOT,," > devel.files

touch management.files
cat <<EndOfList>>management.files
%{python_sitelib}/chroma_agent/action_plugins/manage_*.py[c,o]
%{python_sitelib}/chroma_agent/templates/
/usr/lib/ocf/resource.d/chroma/Target
%{_sbindir}/fence_chroma
%{_sbindir}/chroma-copytool-monitor
%{_sysconfdir}/init/*
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
chkconfig atd on
service atd start
if [ $1 -lt 2 ]; then
    # install
    # open ports in the firewall for access to Lustre
    for port in 988; do
        # don't allow lokkit to re-install the firewall due to RH #1024557
        lokkit -n -p $port:tcp
        # instead live update the firewall
        iptables -I INPUT 4 -m state --state new -p tcp --dport $port -j ACCEPT
    done
elif [ $1 -gt 1 ]; then
    # upgrade
    # do nothing, the manager will restart pacemaker after the updates
    # are complete
    :
fi

%postun management
if [ $1 -lt 1 ]; then
    # close previously opened ports in the firewall for access to Lustre
    ed /etc/sysconfig/iptables <<EOF
/-A INPUT -m state --state NEW -m tcp -p udp --dport 988 -j ACCEPT/d
w
q
EOF
    ed /etc/sysconfig/system-config-firewall <<EOF
/--port=988:tcp/d
w
q
EOF
fi

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
