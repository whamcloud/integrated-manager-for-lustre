# Created by pyp2rpm-3.2.1
%global pypi_name gevent

Name:           python-%{pypi_name}
Version:        1.0.1
Release:        2%{?dist}
Summary:        Coroutine-based network library

License:        TODO
URL:            http://www.gevent.org/
Source0:        https://pypi.python.org/packages/source/g/gevent/gevent-1.0.1.tar.gz
 
BuildRequires:  python2-greenlet
BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-sphinx

%description
gevent_ is a coroutinebased Python networking library.Features include:* Fast
event loop based on libev_. * Lightweight execution units based on greenlet_. *
Familiar API that reuses concepts from the Python standard library. *
Cooperative sockets with SSL support. * DNS queries performed through cares_ or
a threadpool. * Ability to use standard library and 3rd party modules written
for ...

%package -n     python2-%{pypi_name}
Summary:        Coroutine-based network library
 
Requires:       python2-greenlet
%description -n python2-%{pypi_name}
gevent_ is a coroutinebased Python networking library.Features include:* Fast
event loop based on libev_. * Lightweight execution units based on greenlet_. *
Familiar API that reuses concepts from the Python standard library. *
Cooperative sockets with SSL support. * DNS queries performed through cares_ or
a threadpool. * Ability to use standard library and 3rd party modules written
for ...

%package -n python-%{pypi_name}-doc
Summary:        gevent documentation
%description -n python-%{pypi_name}-doc
Documentation for gevent

%prep
%autosetup -n %{pypi_name}-%{version}

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python2} setup.py build
# generate html docs 
PYTHONPATH=$PWD:$PWD/doc sphinx-build doc html
# remove the sphinx-build leftovers
rm -rf html/.{doctrees,buildinfo}

%install
%{__python2} setup.py install --skip-build --root %{buildroot}


%files -n python2-%{pypi_name} 
%doc c-ares/README.cares README.rst
%{python2_sitearch}/%{pypi_name}
%{python2_sitearch}/%{pypi_name}-%{version}-py?.?.egg-info

%files -n python-%{pypi_name}-doc
%doc html 

%changelog
* Wed May 10 2017 Brian J. Murrell <brian.murrell@intel.com> 1.0.1-2
- new package built with tito

* Fri May 05 2017 Brian J. Murrell <brian.murrell@intel.com> 1.0.1-1
- Initial package.
