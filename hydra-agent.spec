%{!?name: %define name hydra-agent}
%{?!version: %define version 0.0.1}
%{?!release: %define release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: The Whamcloud Lustre Monitoring and Adminisration Interface Agent
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
Source1: hydra-agent-init.sh
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Whamcloud, Inc. <info@whamcloud.com>
Url: http://www.whamcloud.com/
BuildRequires: python-setuptools
Requires: python-simplejson python-argparse avahi-python python-daemon python-setuptools libxml2-python
%if 0%{?rhel} > 5
Requires: avahi-dnsconfd
%endif

%description
This is the Whamcloud Monitoring and Adminstration Agent

%package management
Summary: Management functionality layer.
Group: System/Utility
Conflicts: sysklogd
Requires: %{name} = %{version} rsyslog pacemaker 
%if 0%{?rhel} > 5
Requires: fence-agents
%endif
%description management
This package layers on management capabilities for the Whamcloud Hydra Agent.

%prep
%setup -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --root=%{buildroot}
mkdir -p $RPM_BUILD_ROOT/etc/init.d/
cp %{SOURCE1} $RPM_BUILD_ROOT/etc/init.d/hydra-agent

touch management.files
cat <<EndOfList>>management.files
%{python_sitelib}/hydra_agent/cmds/*
%{python_sitelib}/hydra_agent/actions/manage_*
%{python_sitelib}/hydra_agent/rmmod.*
/usr/lib/ocf/resource.d/hydra/Target
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
chkconfig hydra-agent on
# disable SELinux -- it prevents both lustre and pacemaker from working
sed -ie 's/^SELINUX=.*$/SELINUX=disabled/' /etc/selinux/config
# the above only disables on the next boot.  disable it currently, also
echo 0 > /selinux/enforce

%post management
chkconfig rsyslog on
chkconfig corosync on

%files -f base.files
%defattr(-,root,root)
%attr(0755,root,root)/etc/init.d/hydra-agent
%{_bindir}/hydra-agent*
%{python_sitelib}/hydra_agent-*.egg-info/*

%files -f management.files management
%defattr(-,root,root)
