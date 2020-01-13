Name:           iml-docker
Version:        0.1.0
Release:        1%{?dist}
Summary: IML + Docker config

License: MIT
URL: https://github.com/whamcloud/integrated-manager-for-lustre
Source0: iml-docker.tar.gz

%description
%{summary}

%prep
%setup -c


%build


%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_sysconfdir}/iml-docker
cp docker-compose.yml %{buildroot}%{_sysconfdir}/iml-docker


%files
%{_sysconfdir}/iml-docker/docker-compose.yml

%changelog
* Fri Jan 10 2020 Joe Grund <jgrund@whamcloud.com> - 0.1.0-1
- Initial package