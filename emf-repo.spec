# The install directory for the repo
%{?!emf_repo_root: %global emf_repo_root %{_sharedstatedir}/emf}

Name: emf-repo
Version: 0.0.1
# Release Start
Release: 1%{?dist}
# Release End
Summary: EXAScaler Management Framework repositories

License: MIT

URL: https://github.com/whamcloud/exascaler-management-framework
Source0: emf-repo.tar.gz

ExclusiveArch: x86_64

%description
%{summary}

Requires: rust-emf-nginx

%global debug_package %{nil}

%prep
%setup -c

%build

%install
mkdir -p %{buildroot}%{emf_repo_root}
cp -r repo %{buildroot}%{emf_repo_root}/
cp -r apt-repo %{buildroot}%{emf_repo_root}/

%package rpm
Summary: Repo containing RPMs package of EMF
License: MIT
Group: System Environment/Libraries

%description rpm
%{summary}

%files rpm
%{emf_repo_root}/repo/*

%package deb
Summary: Repo containing DEBs package of EMF
License: MIT
Group: System Environment/Libraries

%description deb
%{summary}

%files deb
%{emf_repo_root}/apt-repo/*
