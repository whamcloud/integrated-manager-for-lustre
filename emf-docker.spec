Name:           emf-docker
Version:        0.5.0
# Release Start
Release:    1%{?dist}
# Release End
Summary: EMF + Docker Images and Config

License: MIT
URL: https://github.com/whamcloud/exascaler-management-framework
Source0: emf-docker.tar.gz

Requires: docker-ce
Requires: sed
Requires: rust-emf-cli
Requires: emf-sos-plugin >= 2.4.0
Provides: iml-docker
Obsoletes: iml-docker

%description
%{summary}

%prep
%setup -c


%build


%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_sysconfdir}/emf-docker/setup/branding
mkdir -p %{buildroot}%{_sharedstatedir}
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_unitdir}
cp docker-compose.yml %{buildroot}%{_sysconfdir}/emf-docker
mv emf-images.tgz %{buildroot}%{_sharedstatedir}
mv copy-embedded-settings %{buildroot}%{_bindir}/
mv update-embedded.sh %{buildroot}%{_bindir}/update-embedded
mv emf-docker.service %{buildroot}%{_unitdir}


%files
%{_sysconfdir}/emf-docker
%attr(0640, root, root) %{_sharedstatedir}/emf-images.tgz
%attr(754, root, root) %{_bindir}/update-embedded
%attr(754, root, root) %{_bindir}/copy-embedded-settings
%attr(0644, root, root) %{_unitdir}/emf-docker.service


%post
%systemd_post emf-docker.service


%preun
%systemd_preun emf-docker.service


%postun
%systemd_postun_with_restart emf-docker.service


%changelog
* Thu Dec 10 2020 Will Johnson <wjohnson@whamcloud.com> - 0.5.0-1
- Release 0.5.0

* Mon Feb 03 2020 Joe Grund <jgrund@whamcloud.com> - 0.2.0-1
- Add docker Images
- Add post block to load images
- Add emf cli proxy script

* Fri Jan 10 2020 Joe Grund <jgrund@whamcloud.com> - 0.1.0-1
- Initial package
