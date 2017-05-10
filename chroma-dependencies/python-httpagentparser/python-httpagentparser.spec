# Created by pyp2rpm-3.2.1
%global pypi_name httpagentparser

Name:           python-%{pypi_name}
Version:        1.5.0
Release:        2%{?dist}
Summary:        Extracts OS Browser etc information from http user agent string

License:        http://www.opensource.org/licenses/mit-license.php
URL:            https://github.com/shon/httpagentparser
Source0:        https://pypi.python.org/packages/source/h/httpagentparser/httpagentparser-1.5.0.tar.gz
BuildArch:      noarch
 
BuildRequires:  python2-devel
BuildRequires:  python-setuptools

%description
 Works on Python 2.5+ and Python 3 Detects OS and Browser. Does not aim to be a
full featured agent parser Will not turn into djangohttpagentparser ;)Usage ..
codeblock:: python >>> import httpagentparser >>> s "Mozilla/5.0 (X11; U; Linux
i686; enUS) AppleWebKit/532.9 (KHTML, like Gecko) \ Chrome/5.0.307.11
Safari/532.9" >>> print httpagentparser.simple_detect(s) ('Linux', 'Chrome
5.0.307.11') ...

%package -n     python2-%{pypi_name}
Summary:        Extracts OS Browser etc information from http user agent string

%description -n python2-%{pypi_name}
 Works on Python 2.5+ and Python 3 Detects OS and Browser. Does not aim to be a
full featured agent parser Will not turn into djangohttpagentparser ;)Usage ..
codeblock:: python >>> import httpagentparser >>> s "Mozilla/5.0 (X11; U; Linux
i686; enUS) AppleWebKit/532.9 (KHTML, like Gecko) \ Chrome/5.0.307.11
Safari/532.9" >>> print httpagentparser.simple_detect(s) ('Linux', 'Chrome
5.0.307.11') ...


%prep
%autosetup -n %{pypi_name}-%{version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info

%build
%{__python2} setup.py build

%install
%{__python2} setup.py install --skip-build --root %{buildroot}


%files -n python2-%{pypi_name} 
%doc README.rst
%{python2_sitelib}/%{pypi_name}
%{python2_sitelib}/%{pypi_name}-%{version}-py?.?.egg-info

%changelog
* Wed May 10 2017 Brian J. Murrell <brian.murrell@intel.com> 1.5.0-2
- new package built with tito

* Fri May 05 2017 Brian J. Murrell <brian.murrell@intel.com> 1.5.0-1
- Initial package.
