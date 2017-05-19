%{!?name: %define name chroma-common}
%{?!version: %define version %(%{__python} -c "from chroma_common import version; sys.stdout.write(version())")}
%{?!package_release: %define package_release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: Chroma Common
Name: %{name}
Version: %{version}
Release: %{package_release}%{?dist}
Source0: %{name}-%{version}.tar.gz
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
Vendor: Intel(R) Corporation

%description
Common library containing routines used by both agent and manager.

%prep
%setup -n %{name}-%{version}

%build
%{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --install-lib=%{python_sitelib} --root=%{buildroot}
mkdir -p $RPM_BUILD_ROOT/usr/sbin/

# Nuke .py[c,o] files as they are not needed
find -L $RPM_BUILD_ROOT -type f -name "*.py[c,o]" | xargs rm

touch base.files
for base_file in $(find -L $RPM_BUILD_ROOT -type f -name '*.py'); do
  install_file=${base_file/$RPM_BUILD_ROOT\///}
  echo "${install_file}" >> base.files
done

%clean
rm -rf %{buildroot}

%files -f base.files
%defattr(-,root,root)
%{python_sitelib}/chroma_common-*.egg-info/*
