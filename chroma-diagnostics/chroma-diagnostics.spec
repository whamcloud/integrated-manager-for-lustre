%{!?name: %define name chroma-diagnostics}
%{?!version: %define version %(%{__python} -c "from chroma_diagnostics import version; sys.stdout.write(version())")}
%{?!package_release: %define package_release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: Chroma Diagnostics
Name: %{name}
Version: %{version}
Release: %{package_release}
Source0: %{name}-%{version}.tar.gz
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Intel(R) Corporation
Requires: python-argparse
Requires: xz-lzma-compat

%description
Commandline tool to collect and save data on manager or storage servers for diagnostic analysis. Intended for administrators.

%package devel
Summary: Contains stripped .py files
Group: Development
Requires: %{name} = %{version}-%{release}
%description devel
This package contains the .py files stripped out of the production build.

%prep
%setup -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --install-lib=%{python_sitelib} --install-scripts=%{_bindir} --root=%{buildroot}
mkdir -p $RPM_BUILD_ROOT/usr/sbin/

# Nuke source code (HYD-1849)
find $RPM_BUILD_ROOT%{python_sitelib}/chroma_diagnostics -name "*.py" \
    | sed -e "s,$RPM_BUILD_ROOT,," > devel.files

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%{_bindir}/chroma-diagnostics
%{python_sitelib}/chroma_diagnostics-*.egg-info/*
%{python_sitelib}/chroma_diagnostics/*.py[c,o]

%files -f devel.files devel
%defattr(-,root,root)
