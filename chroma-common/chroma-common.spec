%{!?name: %define name chroma-common}
%{?!version: %define version %(%{__python2} -c "from chroma_common import version; sys.stdout.write(version())")}
%{?!package_release: %define package_release 1}
%{?!python2_sitelib: %define python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: Chroma Common
Name: %{name}
Version: %{version}
Release: %{package_release}%{?dist}
Source0: %{name}-%{version}.tar.gz
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
Vendor: Intel(R) Corporation

%description
Common library containing routines used by both agent and manager.

%prep
%setup -n %{name}-%{version}

%build
%{__python2} setup.py build

%install
rm -rf %{buildroot}
%{__python2} setup.py install --skip-build --install-lib=%{python2_sitelib} --root=%{buildroot}
mkdir -p $RPM_BUILD_ROOT/usr/sbin/

%clean
rm -rf %{buildroot}

%files
%{python2_sitelib}/*
