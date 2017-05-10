%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%endif

Name:           django-picklefield
Version:        0.1.9
Release:        3%{?dist}
Summary:        Implementation of a pickled object field

Group:          Development/Languages
License:        MIT
URL:            http://pypi.python.org/pypi/django-picklefield
Source0:        http://pypi.python.org/packages/source/d/%{name}/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools


%description
django-picklefield provides an implementation of a pickled object field.
Such fields can contain any picklable objects.

The implementation is taken and adopted from Django snippet #1694 by
Taavi Taijala, which is in turn based on Django snippet #513 by
Oliver Beattie.


%prep
%setup -q


%build
%{__python} setup.py build


%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --root %{buildroot}

 
%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc README
%{python_sitelib}/picklefield/
%{python_sitelib}/django_picklefield*.egg-info


%changelog
* Wed May 10 2017 Brian J. Murrell <brian.murrell@intel.com> 0.1.9-3
- new package built with tito

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.1.9-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Wed Nov 08 2010 Fabian Affolter <fabian@bernewireless.net> - 0.1.9-1
- Updated to new upstream version 0.1.9

* Sat Jul 03 2010 Fabian Affolter <fabian@bernewireless.net> - 0.1.6-1
- Initial package
