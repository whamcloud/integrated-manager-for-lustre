%{!?name: %define name chroma-agent}
%{?!version: %define version 0.0.1}
%{?!release: %define release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: Chroma Agent
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
Source1: chroma-agent-init.sh
Source2: lustre-modules-init.sh
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Whamcloud, Inc. <info@whamcloud.com>
Url: http://www.whamcloud.com/
BuildRequires: python-setuptools
Requires: python-simplejson python-argparse python-daemon python-setuptools
Requires(post): selinux-policy

%description
This is the Whamcloud monitoring and adminstration agent

%package management
Summary: Management functionality layer.
Group: System/Utility
Conflicts: sysklogd
Requires: %{name} = %{version}-%{release} rsyslog pacemaker libxml2-python
%if 0%{?rhel} > 5
Requires: fence-agents
%endif
%description management
This package layers on management capabilities for Whamcloud Chroma Agent.

%prep
%setup -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --install-lib=%{python_sitelib} --install-scripts=%{_bindir} --root=%{buildroot}
mkdir -p $RPM_BUILD_ROOT/etc/init.d/
cp %{SOURCE1} $RPM_BUILD_ROOT/etc/init.d/chroma-agent
cp %{SOURCE2} $RPM_BUILD_ROOT/etc/init.d/lustre-modules

touch management.files
cat <<EndOfList>>management.files
%{python_sitelib}/chroma_agent/action_plugins/manage_*
%{python_sitelib}/chroma_agent/rmmod.*
/usr/lib/ocf/resource.d/chroma/Target
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
chkconfig chroma-agent on
chkconfig lustre-modules on
# disable SELinux -- it prevents both lustre and pacemaker from working
sed -ie 's/^SELINUX=.*$/SELINUX=disabled/' /etc/selinux/config
# the above only disables on the next boot.  disable it currently, also
echo 0 > /selinux/enforce

%post management
chkconfig rsyslog on
chkconfig corosync on

%files -f base.files
%defattr(-,root,root)
%attr(0755,root,root)/etc/init.d/chroma-agent
%attr(0755,root,root)/etc/init.d/lustre-modules
%{_bindir}/chroma-agent*
%{python_sitelib}/chroma_agent-*.egg-info/*

%files -f management.files management
%defattr(-,root,root)
