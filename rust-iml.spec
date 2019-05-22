%global crate iml

Name: rust-%{crate}
Version: 0.1.1
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
cp iml-agent %{buildroot}%{_bindir}
cp iml-agent-daemon %{buildroot}%{_bindir}
cp iml-stratagem %{buildroot}%{_bindir}
cp iml-agent-comms %{buildroot}%{_bindir}
cp iml-action-runner %{buildroot}%{_bindir}
cp iml-warp-drive %{buildroot}%{_bindir}
cp iml-mailbox %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_unitdir}
cp iml-stratagem.service %{buildroot}%{_unitdir}
cp iml-agent-comms.service %{buildroot}%{_unitdir}
cp iml-action-runner.{socket,service} %{buildroot}%{_unitdir}
cp rust-iml-agent.{service,path} %{buildroot}%{_unitdir}
cp iml-warp-drive.service %{buildroot}%{_unitdir}
cp iml-mailbox.service %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_presetdir}
cp 00-rust-iml-agent.preset %{buildroot}%{_presetdir}

%package agent
Summary: IML Agent Daemon and CLI
License: MIT
Group: System Environment/Libraries

%description agent
%{summary}

%files agent
%{_bindir}/iml-agent
%{_bindir}/iml-agent-daemon
%attr(0644,root,root)%{_unitdir}/rust-iml-agent.service
%attr(0644,root,root)%{_unitdir}/rust-iml-agent.path
%attr(0644,root,root)%{_presetdir}/00-rust-iml-agent.preset

%post agent
systemctl preset rust-iml-agent.path

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

%package stratagem
Summary: Consumer of IML Agent Stratagem push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-iml-agent-comms

%description stratagem
%{summary}

%post stratagem
systemctl preset iml-stratagem.service

%preun stratagem
%systemd_preun iml-stratagem.service

%postun stratagem
%systemd_postun_with_restart iml-stratagem.service

%files stratagem
%{_bindir}/iml-stratagem
%attr(0644,root,root)%{_unitdir}/iml-stratagem.service

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

%changelog
* Wed Mar 6 2019 Joe Grund <jgrund@whamcloud.com> - 0.1.0-1
- Initial package