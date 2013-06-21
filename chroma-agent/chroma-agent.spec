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
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Whamcloud, Inc. <info@whamcloud.com>
Url: http://www.whamcloud.com/
BuildRequires: python-setuptools
Requires: ntp python-simplejson python-argparse python-daemon python-setuptools python-requests >= 1.0.3
%if 0%{?rhel} > 5
Requires: util-linux-ng
%endif
Requires(post): selinux-policy

%description
This is the Whamcloud monitoring and adminstration agent

%package management
Summary: Management functionality layer.
Group: System/Utility
Conflicts: sysklogd
Requires: %{name} = %{version}-%{release} rsyslog pacemaker-iml python-dateutil >= 1.5 libxml2-python python-netaddr python-ethtool python-jinja2 pcapy python-impacket fence-agents-iml yum-utils system-config-firewall-base
%description management
This package layers on management capabilities for Whamcloud Chroma Agent.

%prep
%setup -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --install-lib=%{python_sitelib} --install-scripts=%{_bindir} --root=%{buildroot}
mkdir -p $RPM_BUILD_ROOT/usr/sbin/
mv $RPM_BUILD_ROOT/usr/{,s}bin/fence_chroma
mkdir -p $RPM_BUILD_ROOT/etc/{init,logrotate}.d/
cp %{SOURCE1} $RPM_BUILD_ROOT/etc/init.d/chroma-agent
cp %{SOURCE2} $RPM_BUILD_ROOT/etc/init.d/lustre-modules
install -m 644 %{SOURCE3} $RPM_BUILD_ROOT/etc/logrotate.d/chroma-agent


touch management.files
cat <<EndOfList>>management.files
%{python_sitelib}/chroma_agent/action_plugins/manage_*
%{python_sitelib}/chroma_agent/templates/
/usr/lib/ocf/resource.d/chroma/Target
%{_sbindir}/fence_chroma
EndOfList

touch base.files
mgmt_patterns=$(cat management.files)
for base_file in $(find $RPM_BUILD_ROOT -type f -name '*.py'); do
  install_file=${base_file/$RPM_BUILD_ROOT\///}
  for mgmt_pat in $mgmt_patterns; do
    if [[ $install_file == $mgmt_pat ]]; then
      continue 2
    fi
  done
  echo "${install_file%.py*}.py*" >> base.files
done

%clean
rm -rf %{buildroot}

%post
chkconfig lustre-modules on
# disable SELinux -- it prevents both lustre and pacemaker from working
sed -ie 's/^SELINUX=.*$/SELINUX=disabled/' /etc/selinux/config
# the above only disables on the next boot.  disable it currently, also
echo 0 > /selinux/enforce

%post management
chkconfig rsyslog on
if [ $1 -lt 2 ]; then
    # open ports in the firewall for access to Lustre
    for port in 988; do
        lokkit -p $port:tcp
    done
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
%files -f base.files
%defattr(-,root,root)
%attr(0755,root,root)/etc/init.d/chroma-agent
%attr(0755,root,root)/etc/init.d/lustre-modules
%{_bindir}/chroma-agent*
%{python_sitelib}/chroma_agent-*.egg-info/*
%attr(0644,root,root)/etc/logrotate.d/chroma-agent

%files -f management.files management
%defattr(-,root,root)
