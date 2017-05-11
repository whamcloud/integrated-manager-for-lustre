# Created by pyp2rpm-3.2.1
%global pypi_name greenlet

Name:           python-%{pypi_name}
Version:        0.4.2
Release:        3%{?dist}
Summary:        Lightweight in-process concurrent programming

License:        MIT License
URL:            https://github.com/python-greenlet/greenlet
Source0:        http://pypi.python.org/packages/source/g/greenlet/greenlet-0.4.2.zip
 
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-sphinx
 
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-setuptools

%description
The greenlet package is a spinoff of Stackless, a version of CPython that
supports microthreads called "tasklets". Tasklets run pseudoconcurrently
(typically in a single or a few OSlevel threads) and are synchronized with data
exchanges on "channels".A "greenlet", on the other hand, is a still more
primitive notion of microthread with no implicit scheduling; coroutines, in
other words. This is ...

%package -n     python2-%{pypi_name}
Summary:        Lightweight in-process concurrent programming

%description -n python2-%{pypi_name}
The greenlet package is a spinoff of Stackless, a version of CPython that
supports microthreads called "tasklets". Tasklets run pseudoconcurrently
(typically in a single or a few OSlevel threads) and are synchronized with data
exchanges on "channels".A "greenlet", on the other hand, is a still more
primitive notion of microthread with no implicit scheduling; coroutines, in
other words. This is ...

%package -n     python%{python3_pkgversion}-%{pypi_name}
Summary:        Lightweight in-process concurrent programming

%description -n python%{python3_pkgversion}-%{pypi_name}
The greenlet package is a spinoff of Stackless, a version of CPython that
supports microthreads called "tasklets". Tasklets run pseudoconcurrently
(typically in a single or a few OSlevel threads) and are synchronized with data
exchanges on "channels".A "greenlet", on the other hand, is a still more
primitive notion of microthread with no implicit scheduling; coroutines, in
other words. This is ...

%package -n python-%{pypi_name}-doc
Summary:        greenlet documentation
%description -n python-%{pypi_name}-doc
Documentation for greenlet

%prep
%autosetup -n %{pypi_name}-%{version}

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python2} setup.py build
CFLAGS="$RPM_OPT_FLAGS" %{__python3} setup.py build
# generate html docs 
sphinx-build doc html
# remove the sphinx-build leftovers
rm -rf html/.{doctrees,buildinfo}

%install
# Must do the subpackages' install first because the scripts in /usr/bin are
# overwritten with every setup.py install.
%{__python3} setup.py install --skip-build --root %{buildroot}

%{__python2} setup.py install --skip-build --root %{buildroot}


%files -n python2-%{pypi_name} 
%{_includedir}/python%{python2_version}
%{_libdir}/python%{python2_version}
%doc README.rst
%{python2_sitearch}/%{pypi_name}-%{version}-py?.?.egg-info

%files -n python%{python3_pkgversion}-%{pypi_name} 
%{_includedir}/python%{python3_version}m
%{_libdir}/python%{python3_version}
%doc README.rst
%{python3_sitearch}/%{pypi_name}-%{version}-py?.?.egg-info

%files -n python-%{pypi_name}-doc
%doc html 

%changelog
* Thu May 11 2017 Brian J. Murrell <brian.murrell@intel.com> 0.4.2-3
- Add missed file due to .gitignore (brian.murrell@intel.com)

* Wed May 10 2017 Brian J. Murrell <brian.murrell@intel.com> 0.4.2-2
- new package built with tito

* Fri May 05 2017 Brian J. Murrell <brian.murrell@intel.com> 0.4.2-1
- Initial package.
