%{!?name: %define name chroma-diagnostics}
%{?!version: %define version %(%{__python} -c "from chroma_diagnostics import version; sys.stdout.write(version())")}
%{?!release: %define release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: Chroma Diagnostics
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Intel(R) Corporation

%description
Commandline tool to collect and save data on manager or storage servers for diagnostic analysis. Intended for administrators.

%prep
%setup -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --install-lib=%{python_sitelib} --install-scripts=%{_bindir} --root=%{buildroot}
mkdir -p $RPM_BUILD_ROOT/usr/sbin/

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%{_bindir}/chroma-diagnostics
%{python_sitelib}/chroma_diagnostics-*.egg-info/*
%{python_sitelib}/chroma_diagnostics/*
