%global docdir %{_docdir}/%{name}-%{version}
%global tmpdir %{_tmppath}/%{name}-tests


Name:           django-tastypie
Version:        0.9.11
Release:        5%{?dist}
Summary:        Tastypie is an webservice API framework for Django

Group:          Development/Languages
License:        BSD
URL:            http://django-tastypie.readthedocs.org/en/latest/index.html
Source0:        http://pypi.python.org/packages/source/d/django-tastypie/%{name}-%{version}.tar.gz
# to get tests:
# git clone https://github.com/toastdriven/django-tastypie.git && cd django-tastypie
# git checkout v0.9.11
# tar -czf django-tastypie-tests.tgz tests/
Source1:        %{name}-tests.tgz

Requires:       python-mimeparse >= 0.1.3
Requires:       python-dateutil >= 1.5
Requires:       python-dateutil < 2.0
Requires:       Django >= 1.2.0

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
# for tests
BuildRequires:  python-mimeparse >= 0.1.3
BuildRequires:  python-dateutil >= 1.5
BuildRequires:  python-dateutil < 2.0
BuildRequires:  Django >= 1.2.0
# this is only an optional dependency, but we want to test it during build
BuildRequires:  python-lxml

%description
Tastypie is an webservice API framework for Django. It provides a convenient,
yet powerful and highly customizable, abstraction for creating REST-style
interfaces.

%package doc
Summary: Documentation for %{name}
Group: Documentation

Requires: %{name} = %{version}-%{release}

%description doc
This package contains documentation for %{name}.

%prep
%setup -q
# move the tests into place
tar xzf %{SOURCE1}
sed -i 's|django-admin.py|django-admin|' tests/run_all_tests.sh


%build
%{__python} setup.py build


%install
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
mkdir -p %{buildroot}%{docdir}
cp -pr docs/_build/html %{buildroot}%{docdir}
cp -p LICENSE README.rst AUTHORS -t %{buildroot}%{docdir}

%check
# note: the oauth tests will work once the proper module gets into rawhide
# from the authors documentation it is now not very clear if it is
# django-oauth or django-oauth-provider or django-oauth-plus
# anyway, it is not a hard requirement
#pushd tests
#./run_all_tests.sh
#popd


%files
%doc %{docdir}/LICENSE
%{python_sitelib}/*

%files doc
%doc %{docdir}
%exclude %{docdir}/html/.buildinfo

%changelog
* Thu May 11 2017 Brian J. Murrell <brian.murrell@intel.com> 0.9.11-5
- Add missed file due to .gitignore (brian.murrell@intel.com)

* Wed May 10 2017 Brian J. Murrell <brian.murrell@intel.com> 0.9.11-4
- new package built with tito

* Thu May 04 2017 Brian J. Murrell <brian.murrell@intel.com> 0.9.11-3
- disable the check scriptlet

* Fri Jan 06 2012 Bohuslav Kabrda <bkabrda@redhat.com> - 0.9.11-2
- Excluded the .buildinfo from html dir.
- Fixed specfile permissions.
- Removed unneeded PYTHONPATH setup during tests.
- Fixed the mixed spaces/tabs rpmlint warning.
- Removed the rm -rf in install section.

* Thu Dec 22 2011 Bohuslav Kabrda <bkabrda@redhat.com> - 0.9.11-1
- Initial package.
