%{?systemd_requires}
BuildRequires: systemd

%global crate iml

Name: rust-%{crate}
Version: 0.2.0
# Release Start
Release: 1%{?dist}
# Release End
Summary: Integrated Manager for Lustre Services

License: MIT

URL: https://github.com/whamcloud/integrated-manager-for-lustre
Source0: rust-iml.tar.gz

ExclusiveArch: x86_64

%description
%{summary}

%prep
%setup -c

%build

%install
mkdir -p %{buildroot}%{_bindir}
cp iml %{buildroot}%{_bindir}
cp iml-agent %{buildroot}%{_bindir}
cp iml-agent-daemon %{buildroot}%{_bindir}
cp iml-api %{buildroot}%{_bindir}
cp iml-ostpool %{buildroot}%{_bindir}
cp iml-device %{buildroot}%{_bindir}
cp iml-stats %{buildroot}%{_bindir}
cp iml-agent-comms %{buildroot}%{_bindir}
cp iml-action-runner %{buildroot}%{_bindir}
cp iml-warp-drive %{buildroot}%{_bindir}
cp iml-mailbox %{buildroot}%{_bindir}
cp iml-ntp %{buildroot}%{_bindir}
cp iml-postoffice %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_unitdir}
cp iml-api.service %{buildroot}%{_unitdir}
cp iml-device.service %{buildroot}%{_unitdir}
cp iml-ostpool.service %{buildroot}%{_unitdir}
cp iml-rust-stats.service %{buildroot}%{_unitdir}
cp iml-agent-comms.service %{buildroot}%{_unitdir}
cp iml-action-runner.{socket,service} %{buildroot}%{_unitdir}
cp rust-iml-agent.{service,path} %{buildroot}%{_unitdir}
cp iml-warp-drive.service %{buildroot}%{_unitdir}
cp iml-mailbox.service %{buildroot}%{_unitdir}
cp iml-ntp.service %{buildroot}%{_unitdir}
cp iml-postoffice.service %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_tmpfilesdir}
cp iml-mailbox.conf %{buildroot}%{_tmpfilesdir}
cp tmpfiles.conf %{buildroot}%{_tmpfilesdir}/iml-agent.conf
mkdir -p %{buildroot}%{_presetdir}
cp 00-rust-iml-agent.preset %{buildroot}%{_presetdir}
mkdir -p %{buildroot}%{_sysconfdir}/iml/
cp settings.conf %{buildroot}%{_sysconfdir}/iml/iml-agent.conf

%package cli
Summary: IML manager CLI
License: MIT
Group: System Environment/Libraries

%description cli
%{summary}

%files cli
%{_bindir}/iml

%package agent
Summary: IML Agent Daemon and CLI
License: MIT
Group: System Environment/Libraries
Requires: iml-device-scanner >= 4.0
Obsoletes: iml-device-scanner-proxy

%description agent
%{summary}

%files agent
%{_bindir}/iml-agent
%{_bindir}/iml-agent-daemon
%attr(0644,root,root)
%{_sysconfdir}/iml/iml-agent.conf
%{_unitdir}/rust-iml-agent.service
%{_unitdir}/rust-iml-agent.path
%{_presetdir}/00-rust-iml-agent.preset
%{_tmpfilesdir}/iml-agent.conf

%post agent
systemctl preset rust-iml-agent.path
%tmpfiles_create %{_tmpfilesdir}/iml-agent.conf

%preun agent
%systemd_preun rust-iml-agent.path
%systemd_preun rust-iml-agent.service

%postun agent
%systemd_postun_with_restart rust-iml-agent.path

%package agent-comms
Summary: Communicates with iml-agents
License: MIT
Group: System Environment/Libraries

%description agent-comms
%{summary}

%post agent-comms
systemctl preset iml-agent-comms.service

%preun agent-comms
%systemd_preun iml-agent-comms.service

%postun agent-comms
%systemd_postun_with_restart iml-agent-comms.service

%files agent-comms
%{_bindir}/iml-agent-comms
%attr(0644,root,root)%{_unitdir}/iml-agent-comms.service

%package api
Summary: Standalone Rust API build on warp
License: MIT
Group: System Environment/Libraries

%description api
%{summary}

%post api
systemctl preset iml-api.service

%preun api
%systemd_preun iml-api.service

%postun api
%systemd_postun_with_restart iml-api.service

%files api
%{_bindir}/iml-api
%attr(0644,root,root)%{_unitdir}/iml-api.service

%package action-runner
Summary: Dispatches and tracks RPCs to agents
License: MIT
Group: System Environment/Libraries

%description action-runner
%{summary}

%post action-runner
systemctl preset iml-action-runner.socket
systemctl preset iml-action-runner.service

%preun action-runner
%systemd_preun iml-action-runner.socket
%systemd_preun iml-action-runner.service

%postun action-runner
%systemd_postun_with_restart iml-action-runner.socket
%systemd_postun_with_restart iml-action-runner.service

%files action-runner
%{_bindir}/iml-action-runner
%attr(0644,root,root)%{_unitdir}/iml-action-runner.socket
%attr(0644,root,root)%{_unitdir}/iml-action-runner.service

%package ostpool
Summary: Consumer of IML Agent Ostpool push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-iml-agent-comms

%description ostpool
%{summary}

%post ostpool
systemctl preset iml-ostpool.service

%preun ostpool
%systemd_preun iml-ostpool.service

%postun ostpool
%systemd_postun_with_restart iml-ostpool.service

%files ostpool
%{_bindir}/iml-ostpool
%attr(0644,root,root)%{_unitdir}/iml-ostpool.service

%package stats
Summary: Consumer of IML stats
License: MIT
Group: System Environment/Libraries
Requires: rust-iml-agent-comms

%description stats
%{summary}

%post stats
systemctl preset iml-rust-stats.service

%preun stats
%systemd_preun iml-rust-stats.service

%postun stats
%systemd_postun_with_restart iml-rust-stats.service

%files stats
%{_bindir}/iml-stats
%attr(0644,root,root)%{_unitdir}/iml-rust-stats.service

%package warp-drive
Summary: Streaming IML messages with Server-Sent Events
License: MIT
Group: System Environment/Libraries

%description warp-drive
%{summary}

%post warp-drive
systemctl preset iml-warp-drive.service

%preun warp-drive
%systemd_preun iml-warp-drive.service

%postun warp-drive
%systemd_postun_with_restart iml-warp-drive.service

%files warp-drive
%{_bindir}/iml-warp-drive
%attr(0644,root,root)%{_unitdir}/iml-warp-drive.service

%package mailbox
Summary: Performs bidirectional streaming of large datasets
License: MIT
Group: System Environment/Libraries

%description mailbox
%{summary}

%post mailbox
systemctl preset iml-mailbox.service

%preun mailbox
%systemd_preun mailbox.service

%postun mailbox
%systemd_postun_with_restart mailbox.service

%files mailbox
%{_bindir}/iml-mailbox
%attr(0644,root,root)%{_unitdir}/iml-mailbox.service
%attr(0644,root,root)%{_tmpfilesdir}/iml-mailbox.conf

%package ntp
Summary: Consumer of IML Agent Ntp push queue
License: MIT
Group: System Environment/Libraries

%description ntp
%{summary}

%post ntp
systemctl preset iml-ntp.service

%preun ntp
%systemd_preun iml-ntp.service

%postun ntp
%systemd_postun_with_restart iml-ntp.service

%files ntp
%{_bindir}/iml-ntp
%attr(0644,root,root)%{_unitdir}/iml-ntp.service

%package postoffice
Summary: Consumer of IML Agent Postoffice push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-iml-agent-comms

%description postoffice
%{summary}

%post postoffice
systemctl preset iml-postoffice.service

%preun postoffice
%systemd_preun iml-postoffice.service

%postun postoffice
%systemd_postun_with_restart iml-postoffice.service

%files postoffice
%{_bindir}/iml-postoffice
%attr(0644,root,root)%{_unitdir}/iml-postoffice.service

%package device
Summary: Consumer of IML Agent device push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-iml-agent-comms

%description device
%{summary}

%post device
systemctl preset iml-device.service

%preun device
%systemd_preun iml-device.service

%postun device
%systemd_postun_with_restart iml-device.service

%files device
%{_bindir}/iml-device
%attr(0644,root,root)%{_unitdir}/iml-device.service

%changelog
* Wed Sep 18 2019 Will Johnson <wjohnson@whamcloud.com> - 0.2.0-1 
- Add ntp service

* Wed Mar 6 2019 Joe Grund <jgrund@whamcloud.com> - 0.1.0-1
- Initial package
