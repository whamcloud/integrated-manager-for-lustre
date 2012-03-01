%{!?name: %define name django-r3d}
%{?!version: %define version 0.0.1}
%{?!release: %define release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: Relational Round-Robin Databases (R3D) for Django
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Whamcloud, Inc. <info@whamcloud.com>
Url: http://www.whamcloud.com/
BuildRequires: python-setuptools
Requires: Django-south >= 0.7.2 python-setuptools

%description
R3D provides round-robin databases for time-series data implemented via
Django's ORM layer.  It is a mostly-faithful copy of Tobi Oetiker's
rrdtool implementation, and provides the same basic Datasource/Archive
types.

%prep
%setup -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --root=%{buildroot}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%{python_sitelib}/*
