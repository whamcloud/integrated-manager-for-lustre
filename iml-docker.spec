Name:           iml-docker
Version:        0.5.0
# Release Start
Release:    1%{?dist}
# Release End
Summary: IML + Docker Images and Config

License: MIT
URL: https://github.com/whamcloud/integrated-manager-for-lustre
Source0: iml-docker.tar.gz

Requires: docker-ce
Requires: sed
Requires: rust-iml-cli
Requires: emf-sos-plugin >= 2.4.0

%description
%{summary}

%prep
%setup -c


%build


%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_sysconfdir}/iml-docker/setup/branding
mkdir -p %{buildroot}%{_sharedstatedir}
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_unitdir}
cp docker-compose.yml %{buildroot}%{_sysconfdir}/iml-docker
mv iml-images.tgz %{buildroot}%{_sharedstatedir}
mv copy-embedded-settings %{buildroot}%{_bindir}/
mv update-embedded.sh %{buildroot}%{_bindir}/update-embedded
mv iml-docker.service %{buildroot}%{_unitdir}


%files
%{_sysconfdir}/iml-docker
%attr(0640, root, root) %{_sharedstatedir}/iml-images.tgz
%attr(754, root, root) %{_bindir}/update-embedded
%attr(754, root, root) %{_bindir}/copy-embedded-settings
%attr(0644, root, root) %{_unitdir}/iml-docker.service


%post
%systemd_post iml-docker.service


%preun
%systemd_preun iml-docker.service


%postun
%systemd_postun_with_restart iml-docker.service


%changelog
* Thu Dec 10 2020 Will Johnson <wjohnson@whamcloud.com> - 0.5.0-1
- Release 0.5.0

* Mon Feb 03 2020 Joe Grund <jgrund@whamcloud.com> - 0.2.0-1
- Add docker Images
- Add post block to load images
- Add iml cli proxy script

* Fri Jan 10 2020 Joe Grund <jgrund@whamcloud.com> - 0.1.0-1
- Initial package
