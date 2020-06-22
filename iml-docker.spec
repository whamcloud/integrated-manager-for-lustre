Name:           iml-docker
Version:        0.3.0
# Release Start
Release:    1%{?dist}
# Release End
Summary: IML + Docker Images and Config

License: MIT
URL: https://github.com/whamcloud/integrated-manager-for-lustre
Source0: iml-docker.tar.gz

Requires: docker-ce
Requires: sed

%description
%{summary}

%prep
%setup -c


%build


%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_sysconfdir}/iml-docker/setup
mkdir -p %{buildroot}%{_tmppath}
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_unitdir}
cp docker-compose.yml %{buildroot}%{_sysconfdir}/iml-docker
mv iml-images.tgz %{buildroot}%{_tmppath}
mv iml-cli-proxy.sh %{buildroot}%{_bindir}/iml
mv update-embedded.sh %{buildroot}%{_bindir}/update-embedded
mv iml-docker.service %{buildroot}%{_unitdir}


%files
%{_sysconfdir}/iml-docker
%attr(750, root, root) %config(missingok) %{_tmppath}/iml-images.tgz
%attr(754, root, root) %{_bindir}/iml
%attr(754, root, root) %{_bindir}/update-embedded
%attr(0644,root,root) %{_unitdir}/iml-docker.service


%post
systemctl preset iml-docker.service

%preun
%systemd_preun iml-docker.service


%postun
%systemd_postun_with_restart iml-docker.service


%changelog
* Mon Feb 03 2020 Joe Grund <jgrund@whamcloud.com> - 0.2.0-1
- Add docker Images
- Add post block to load images
- Add iml cli proxy script

* Fri Jan 10 2020 Joe Grund <jgrund@whamcloud.com> - 0.1.0-1
- Initial package
