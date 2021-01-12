%define     base_name device-scanner

Name:       emf-%{base_name}
Version:    5.1.0
# Release Start
Release:    1%{?dist}
# Release End
Summary:    Maintains data of block devices

License:    MIT
Group:      System Environment/Libraries
URL:        https://github.com/whamcloud/%{base_name}
Source0:    emf-device-scanner.tar.gz

%{?systemd_requires}

Autoreq:  0
Requires: socat
Provides: iml-device-scanner
Obsoletes: iml-device-scanner

%description
device-scanner-daemon builds an in-memory representation of
devices using udev and findmnt.

%prep
%setup -c

%build

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_presetdir}
mkdir -p %{buildroot}%{_sysconfdir}/udev/rules.d

cp device-scanner.{target,socket,service} %{buildroot}%{_unitdir}
cp block-device-populator.service %{buildroot}%{_unitdir}
cp 00-device-scanner.preset %{buildroot}%{_presetdir}
cp device-scanner-daemon %{buildroot}%{_bindir}

cp 99-emf-device-scanner.rules %{buildroot}%{_sysconfdir}/udev/rules.d
cp uevent-listener %{buildroot}%{_bindir}

cp mount-emitter.service %{buildroot}%{_unitdir}
cp mount-populator.service %{buildroot}%{_unitdir}
cp swap-emitter.service %{buildroot}%{_unitdir}
cp mount-emitter %{buildroot}%{_bindir}
cp swap-emitter %{buildroot}%{_bindir}

%files
%attr(0644,root,root)%{_unitdir}/block-device-populator.service
%attr(0644,root,root)%{_unitdir}/device-scanner.target
%attr(0644,root,root)%{_unitdir}/device-scanner.socket
%attr(0644,root,root)%{_unitdir}/device-scanner.service
%attr(0644,root,root)%{_unitdir}/mount-emitter.service
%attr(0644,root,root)%{_unitdir}/mount-populator.service
%attr(0644,root,root)%{_unitdir}/swap-emitter.service
%attr(0644,root,root)%{_presetdir}/00-device-scanner.preset
%attr(0644,root,root)%{_sysconfdir}/udev/rules.d/99-emf-device-scanner.rules
%attr(0755,root,root)%{_bindir}/device-scanner-daemon
%attr(0755,root,root)%{_bindir}/uevent-listener
%attr(0755,root,root)%{_bindir}/mount-emitter
%attr(0755,root,root)%{_bindir}/swap-emitter


%post
%systemd_post device-scanner.socket
%systemd_post mount-emitter.service
%systemd_post swap-emitter.service


%preun
%systemd_preun device-scanner.target
%systemd_preun device-scanner.socket
%systemd_preun device-scanner.service
%systemd_preun mount-emitter.service
%systemd_preun block-device-populator.service
%systemd_preun mount-populator.service
%systemd_preun swap-emitter.service


%postun
%systemd_postun device-scanner.socket


%changelog
* Fri Dec 11 2020 Will Johnson <wjohnson@whamcloud.com> 5.1.0-1
- Released with EMF 6.3

* Thu Oct 18 2018 Joe Grund <jgrund@whamcloud.com> 2.0.0-1
- Resolve device graph agent-side
- Rewrite in Rust

* Tue Jun 26 2018 Joe Grund <joe.grund@whamcloud.com> - 2.0.0-1
- Remove module-tools
- Remove vg_size check

* Mon May 14 2018 Tom Nabarro <tom.nabarro@intel.com> - 2.0.0-1
- Add mount detection to device-scanner
- Integrate device-aggregator
- Move device munging inside aggregator

* Mon Feb 26 2018 Tom Nabarro <tom.nabarro@intel.com> - 2.0.0-1
- Make scanner-proxy a sub-package (separate rpm)
- Handle upgrade scenarios

* Thu Feb 15 2018 Tom Nabarro <tom.nabarro@intel.com> - 2.0.0-1
- Minor change, integrate scanner-proxy project

* Mon Jan 22 2018 Joe Grund <joe.grund@intel.com> - 2.0.0-1
- Breaking change, the API has changed output format


* Wed Sep 27 2017 Joe Grund <joe.grund@intel.com> - 1.1.1-1
- Fix bug where devices weren't removed.
- Cast empty EMF_SIZE string to None.

* Thu Sep 21 2017 Joe Grund <joe.grund@intel.com> - 1.1.0-1
- Exclude unneeded devices.
- Get device ro status.
- Remove manual udev parsing.
- Remove socat as dep, device-scanner will listen to change events directly.

* Mon Sep 18 2017 Joe Grund <joe.grund@intel.com> - 1.0.2-1
- Fix missing keys to be option types.
- Add rules for scsi ids
- Add keys on change|add so we can `udevadm trigger` after install
- Trigger udevadm change event after install
- Read new state into scanner after install

* Tue Aug 29 2017 Joe Grund <joe.grund@intel.com> - 1.0.1-1
- initial package
