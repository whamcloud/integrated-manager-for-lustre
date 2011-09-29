%{!?name: %define name hydra-agent}
%{?!version: %define version 0.0.1}
%{?!release: %define release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: The Whamcloud Lustre Monitoring and Adminisration Interface Agent
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
Source1: hydra-server.conf
Source2: hydra-worker-init.sh
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Whamcloud, Inc. <info@whamcloud.com>
Url: http://www.whamcloud.com/
Requires: python-simplejson python-argparse rsyslog

%description
This is the Whamcloud Monitoring and Adminstration Interface

%prep
%setup -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --root=%{buildroot}

%clean
rm -rf %{buildroot}

%post
chkconfig rsyslog on

%files
%defattr(-,root,root)
%{_bindir}/hydra-agent.py*
%{python_sitelib}/*
/usr/lib/ocf/resource.d/hydra/Target
