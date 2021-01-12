Name: emf-sos-plugin
Version: 2.4.0
# Release Start
Release: 1%{?dist}
# Release End

Summary: EMF sosreport plugin
License: MIT
Group: Applications/System
Vendor: Whamcloud <emf@whamcloud.com>
Packager: EMF Team <emf@whamcloud.com>
Url: https://pypi.python.org/pypi/emf-sos-plugin

Source0: %{name}-%{version}.tar.bz2
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch

Requires: sos < 4.0
Provides: iml_sos_plugin
Obsoletes: iml_sos_plugin

%description
A sosreport plugin for collecting EMF/EMF data

%prep
%setup

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
