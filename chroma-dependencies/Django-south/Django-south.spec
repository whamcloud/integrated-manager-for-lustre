%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           Django-south
Version:        0.7.5
Release:        2%{?dist}
Summary:        Intelligent schema migrations for Django apps

Group:          Development/Languages
License:        ASL 2.0
URL:            http://south.aeracode.org
Source:         http://www.aeracode.org/releases/south/south-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel python-setuptools-devel 
Requires:       Django

%description
South brings migrations to Django applications. Its main objectives are to
provide a simple, stable and database-independent migration layer to prevent
all the hassle schema changes over time bring to your Django applications.

%prep
%setup -q -n South-%{version}

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%{python_sitelib}/*

%changelog
* Wed Jul 18 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.7.5-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Thu May 31 2012 Domingo Becker <domingobecker@gmail.com> - 0.7.5-1
- New upstream version.
- Remove docs dir in files section.
- Fixed unpacked directory name.

* Mon Dec 20 2010 Domingo Becker <domingobecker@gmail.com> - 0.7.3-1
- New upstream version.

* Thu Nov 05 2010 Diego Búrigo Zacarão <diegobz@gmail.com> 0.7.2-2
- Added patch by beckerde

* Mon Sep 27 2010 Domingo Becker <domingobecker@gmail.com> - 0.7.2-1
- Updated to 0.7.2 Release
- A patch is included for python 2.4 compatibility

* Sat Jul 24 2010 Diego Búrigo Zacarão <diegobz@gmail.com> 0.7.1-2
- Updated to 0.7.1 Release

* Sat Oct 24 2009 Diego Búrigo Zacarão <diegobz@gmail.com> 0.6.1-1
- Updated to 0.6.1 Release

* Wed Aug 13 2009 Diego Búrigo Zacarão <diegobz@gmail.com> 0.6-2
- Updated SPEC to use the upstream tar.gz instead of the VCS checkout

* Sun Aug 11 2009 Diego Búrigo Zacarão <diegobz@gmail.com> 0.6-1
- Updated to 0.6 Release

* Sun Aug 11 2009 Diego Búrigo Zacarão <diegobz@gmail.com> 0.6-0.1.20090811hgrc1
- Initial RPM release
