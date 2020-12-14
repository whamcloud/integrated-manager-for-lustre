# Created by pyp2rpm-3.2.2
%global pypi_name iml-common
%{!?name: %global name python2-%{pypi_name}}
%{?!version: %global version 1.4.5}
%global major_minor %(version="%{version}"; v=($(echo ${version//./ })); echo ${v[0]}.${v[1]})
%global rpm_name %{pypi_name}%{major_minor}

%{?dist_version: %global source https://github.com/whamcloud/%{pypi_name}/archive/%{dist_version}.tar.gz}
%{?dist_version: %global archive_version %{dist_version}}
%{?!dist_version: %global source https://files.pythonhosted.org/packages/source/i/%{pypi_name}/%{pypi_name}-%{version}.tar.gz}
%{?!dist_version: %global archive_version %{version}}

Name:           python-%{rpm_name}
Version:        1.4.5
# Release Start
Release:    1%{?dist}
# Release End
Summary:        Common library used by multiple IML components
License:        MIT
URL:            https://pypi.python.org/pypi/%{pypi_name}
Source0:        %{source}
Group: Development/Libraries
BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools

%description
A Python package that contains common components for the IML project Different
areas of the IML project utilise common code that is shared distributed through
this package.This packaging intends to improve code reuse and componentization
within the IML project.

%package -n     python2-%{rpm_name}
Summary:        %{summary}
%{?python_provide:%python_provide python2-%{rpm_name}}
Obsoletes:       python2-%{pypi_name}1.0 python2-%{pypi_name}1.1
Obsoletes:       python2-%{pypi_name}1.2 python2-%{pypi_name}1.3

%description -n python2-%{rpm_name}
A Python package that contains common components for the IML project.  Different
areas of the IML project utilise common code that is shared distributed through
this package.  This packaging intends to improve code reuse and componentization
within the IML project.

%prep
%if %{?dist_version:1}%{!?dist_version:0}
%setup -n %{pypi_name}-%(echo %{archive_version} | sed -Ee '/^v([0-9]+\.)[0-9]+/s/^v(.*)/\1/')
%else
%setup -c -n %{rpm_name}-%{version}
# Remove bundled egg-info
rm -rf %{rpm_name}.egg-info
cd ..
mv %{rpm_name}-%{version}/%{pypi_name}-%{version} ./%{pypi_name}-%{version}
rmdir %{rpm_name}-%{version}
mv %{pypi_name}-%{version} %{rpm_name}-%{version}
%endif

%build
%{__python} setup.py build

%install
%{__python} setup.py install --skip-build --root %{buildroot}

%check
%{__python} setup.py test

%files -n python2-%{rpm_name}
%defattr(-,root,root,-)
%license license.txt
%doc README.md README.rst
%{python2_sitelib}/iml_common
%{python2_sitelib}/%(a=%{pypi_name}; echo ${a//-/_})-*.egg-info/*

%changelog
* Tue Apr 30 2019 Joe Grund <jgrund@whamcloud.com> 1.4.5-1
- Update to imlteam/copr build system

* Tue May 29 2018 Brian J. Murrell <brian.murrell@intel.com> 1.4.4-2
- Add Obsoletes: python2-iml-common1.x

* Fri May 18 2018 Tom Nabarro <tom.nabarro@intel.com> 1.4.4-1
- Fix bug where module is checked for before loading

* Thu May 17 2018 Tom Nabarro <tom.nabarro@intel.com> 1.4.3-1
- Remove use of modprobe to test presence of kernel modules.
- Remove unused FirewallControl classes and relevant tests.

* Tue May 8 2018 Joe Grund <joe.grund@intel.com> 1.4.2-1
- Add back missing commit.

* Tue Mar 13 2018 Joe Grund <joe.grund@intel.com> 1.4.1-1
- include missing files.

* Tue Mar 13 2018 Brian J. Murrell <brian.murrell@intel.com> 1.4.0-1
- Package in stand-alone module

* Tue Feb 13 2018 Tom Nabarro <tom.nabarro@intel.com> 1.3.3-2
- Add explicit dependency on python-lockfile

* Tue Oct 17 2017 Tom Nabarro <tom.nabarro@intel.com> 1.3.3-1
- Update to upstream 1.3.3

* Wed Oct 11 2017 Tom Nabarro <tom.nabarro@intel.com> 1.3.2-1
- Update to upstream 1.3.2

* Tue Oct 10 2017 Joe Grund <joe.grund@intel.com> 1.3.1-1
- Update to upstream 1.3.1

* Wed Oct 04 2017 Joe Grund <joe.grund@intel.com> 1.3.0-1
- Update to upstream 1.3.0

* Tue Oct 03 2017 Brian J. Murrell <brian.murrell@intel.com> 1.2.0-1
- Update to upstream 1.2.0

* Thu Sep 28 2017  - 1.1.1-1
- Remove zfs object store on agent initialisation and termination.

* Fri Sep 15 2017  - 1.1.0-1
- Updates to remove force zpool imports.

* Fri Sep 15 2017  - 1.0.7-1

* Thu Aug 10 2017  - 1.0.6-1
- Initial package.
