%{!?name: %define name chroma-cluster-sim}
%{?!version: %define version %(%{__python} -c "from cluster_sim import version; sys.stdout.write(version())")}
%{?!package_release: %define package_release 1}
%{?!python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; import sys; sys.stdout.write(get_python_lib())")}

Summary: Chroma Cluster Simulator
Name: %{name}
Version: %{version}
Release: %{package_release}%{dist}
Source0: %{name}-%{version}.tar.gz
License: Proprietary
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Intel Corporation <hpdd-info@intel.com>
Url: http://lustre.intel.com/
BuildRequires: python-setuptools
Requires: python-argparse python-setuptools python-requests >= 2.6.0 chroma-agent = %{version}-%{release}

%description
Simulates a cluster of storage servers. Intended for developers.

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
%{_bindir}/cluster-sim
%{_bindir}/cluster-power
%{_bindir}/cluster-sim-benchmark
%{python_sitelib}/chroma_cluster_sim-*.egg-info/*
%{python_sitelib}/cluster_sim/*
