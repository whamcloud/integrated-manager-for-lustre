%{?systemd_requires}
BuildRequires: systemd

%global crate iml

Name: rust-%{crate}
Version: 0.5.0
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
cp iml-action-runner %{buildroot}%{_bindir}
cp iml-agent %{buildroot}%{_bindir}
cp iml-agent-comms %{buildroot}%{_bindir}
cp iml-agent-daemon %{buildroot}%{_bindir}
cp iml-api %{buildroot}%{_bindir}
cp iml-config %{buildroot}%{_bindir}
cp iml-corosync %{buildroot}%{_bindir}
cp iml-device %{buildroot}%{_bindir}
cp iml-journal %{buildroot}%{_bindir}
cp iml-mailbox %{buildroot}%{_bindir}
cp iml-network %{buildroot}%{_bindir}
cp iml-ntp %{buildroot}%{_bindir}
cp iml-ostpool %{buildroot}%{_bindir}
cp iml-postoffice %{buildroot}%{_bindir}
cp iml-report %{buildroot}%{_bindir}
cp iml-sfa %{buildroot}%{_bindir}
cp iml-snapshot %{buildroot}%{_bindir}
cp iml-stats %{buildroot}%{_bindir}
cp iml-task-runner %{buildroot}%{_bindir}
cp iml-warp-drive %{buildroot}%{_bindir}
cp iml-timer %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_unitdir}
cp iml-action-runner.{socket,service} %{buildroot}%{_unitdir}
cp iml-agent-comms.service %{buildroot}%{_unitdir}
cp iml-api.service %{buildroot}%{_unitdir}
cp iml-rust-corosync.service %{buildroot}%{_unitdir}
cp iml-device.service %{buildroot}%{_unitdir}
cp iml-journal.service %{buildroot}%{_unitdir}
cp iml-mailbox.service %{buildroot}%{_unitdir}
cp iml-network.service %{buildroot}%{_unitdir}
cp iml-ntp.service %{buildroot}%{_unitdir}
cp iml-ostpool.service %{buildroot}%{_unitdir}
cp iml-postoffice.service %{buildroot}%{_unitdir}
cp iml-report.service %{buildroot}%{_unitdir}
cp iml-rust-stats.service %{buildroot}%{_unitdir}
cp iml-sfa.service %{buildroot}%{_unitdir}
cp iml-snapshot.service %{buildroot}%{_unitdir}
cp iml-task-runner.service %{buildroot}%{_unitdir}
cp iml-warp-drive.service %{buildroot}%{_unitdir}
cp iml-timer.service %{buildroot}%{_unitdir}
cp rust-iml-agent.{service,path} %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_tmpfilesdir}
cp iml-report.conf %{buildroot}%{_tmpfilesdir}
cp tmpfiles.conf %{buildroot}%{_tmpfilesdir}/iml-agent.conf
mkdir -p %{buildroot}%{_presetdir}
cp 00-rust-iml-agent.preset %{buildroot}%{_presetdir}
mkdir -p %{buildroot}%{_sysconfdir}/iml/
cp settings.conf %{buildroot}%{_sysconfdir}/iml/iml-agent.conf
mkdir -p %{buildroot}%{_sysconfdir}/bash_completion.d
%{buildroot}%{_bindir}/iml shell-completion bash -e iml -o %{buildroot}%{_sysconfdir}/bash_completion.d/iml
mkdir -p %{buildroot}%{_datadir}/zsh/site-functions
%{buildroot}%{_bindir}/iml shell-completion zsh -e iml -o %{buildroot}%{_datadir}/zsh/site-functions/_iml

%package cli
Summary: IML manager CLI
License: MIT
Group: System Environment/Libraries

%description cli
%{summary}

%files cli
%{_bindir}/iml

%package cli-bash-completion
Summary: IML manager CLI (bash completion script)
License: MIT
Group: System Environment/Libraries

%description cli-bash-completion
%{summary}

%files cli-bash-completion
%{_sysconfdir}/bash_completion.d/iml

%package cli-zsh-completion
Summary: IML manager CLI (zsh completion script)
License: MIT
Group: System Environment/Libraries

%description cli-zsh-completion
%{summary}

%files cli-zsh-completion
%{_datadir}/zsh/site-functions/_iml

%package config-cli
Summary: IML manager Config CLI
License: MIT
Group: System Environment/Libraries

%description config-cli
%{summary}

%files config-cli
%{_bindir}/iml-config

%package agent
Summary: IML Agent Daemon and CLI
License: MIT
Group: System Environment/Libraries
Requires: systemd-journal-gateway
Requires: iml-device-scanner >= 5.1
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
%systemd_post rust-iml-agent.path
%systemd_post systemd-journal-gatewayd.socket
%tmpfiles_create %{_tmpfilesdir}/iml-agent.conf

%preun agent
%systemd_preun rust-iml-agent.path
%systemd_preun rust-iml-agent.service

%postun agent
%systemd_postun_with_restart rust-iml-agent.path
%systemd_postun_with_restart systemd-journal-gatewayd.socket

%package agent-comms
Summary: Communicates with iml-agents
License: MIT
Group: System Environment/Libraries

%description agent-comms
%{summary}

%post agent-comms
%systemd_post iml-agent-comms.service

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
%systemd_post iml-api.service

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
%systemd_post iml-action-runner.socket
%systemd_post iml-action-runner.service

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
%systemd_post iml-ostpool.service

%preun ostpool
%systemd_preun iml-ostpool.service

%postun ostpool
%systemd_postun_with_restart iml-ostpool.service

%files ostpool
%{_bindir}/iml-ostpool
%attr(0644,root,root)%{_unitdir}/iml-ostpool.service

%package task-runner
Summary: Dispatches and tracks Tasks to Client Workers
License: MIT
Group: System Environment/Libraries

%description task-runner
%{summary}

%post task-runner
%systemd_post iml-task-runner.service

%preun task-runner
%systemd_preun iml-task-runner.service

%postun task-runner
%systemd_postun_with_restart iml-task-runner.service

%files task-runner
%{_bindir}/iml-task-runner
%attr(0644,root,root)%{_unitdir}/iml-task-runner.service

%package stats
Summary: Consumer of IML stats
License: MIT
Group: System Environment/Libraries
Requires: rust-iml-agent-comms

%description stats
%{summary}

%post stats
%systemd_post iml-rust-stats.service

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
%systemd_post iml-warp-drive.service

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
%systemd_post iml-mailbox.service

%preun mailbox
%systemd_preun mailbox.service

%postun mailbox
%systemd_postun_with_restart mailbox.service

%files mailbox
%{_bindir}/iml-mailbox
%attr(0644,root,root)%{_unitdir}/iml-mailbox.service

%package network
Summary: Consumer of IML Agent Network push queue
License: MIT
Group: System Environment/Libraries

%description network
%{summary}

%post network
%systemd_post iml-network.service

%preun network
%systemd_preun iml-network.service

%postun network
%systemd_postun_with_restart iml-network.service

%files network
%{_bindir}/iml-network
%attr(0644,root,root)%{_unitdir}/iml-network.service

%package ntp
Summary: Consumer of IML Agent Ntp push queue
License: MIT
Group: System Environment/Libraries

%description ntp
%{summary}

%post ntp
%systemd_post iml-ntp.service

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
%systemd_post iml-postoffice.service

%preun postoffice
%systemd_preun iml-postoffice.service

%postun postoffice
%systemd_postun_with_restart iml-postoffice.service

%files postoffice
%{_bindir}/iml-postoffice
%attr(0644,root,root)%{_unitdir}/iml-postoffice.service

%package report
Summary: Performs bidirectional streaming of large datasets
License: MIT
Group: System Environment/Libraries

%description report
%{summary}

%post report
%systemd_post iml-report.service

%preun report
%systemd_preun report.service

%postun report
%systemd_postun_with_restart report.service

%files report
%{_bindir}/iml-report
%attr(0644,root,root)%{_unitdir}/iml-report.service
%attr(0644,root,root)%{_tmpfilesdir}/iml-report.conf

%package sfa
Summary: Consumer of SFA API calls
License: MIT
Group: System Environment/Libraries

%description sfa
%{summary}

%post sfa
%systemd_post iml-sfa.service

%preun sfa
%systemd_preun iml-sfa.service

%postun sfa
%systemd_postun_with_restart iml-sfa.service

%files sfa
%{_bindir}/iml-sfa
%attr(0644,root,root)%{_unitdir}/iml-sfa.service

%package snapshot
Summary: Consumer of snapshot listing
License: MIT
Group: System Environment/Libraries
Requires: rust-iml-agent-comms

%description snapshot
%{summary}

%post snapshot
%systemd_post iml-snapshot.service

%preun snapshot
%systemd_preun iml-snapshot.service

%postun snapshot
%systemd_postun_with_restart iml-snapshot.service

%files snapshot
%{_bindir}/iml-snapshot
%attr(0644,root,root)%{_unitdir}/iml-snapshot.service

%package device
Summary: Consumer of IML Agent device push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-iml-agent-comms

%description device
%{summary}

%post device
%systemd_post iml-device.service

%preun device
%systemd_preun iml-device.service

%postun device
%systemd_postun_with_restart iml-device.service

%files device
%{_bindir}/iml-device
%attr(0644,root,root)%{_unitdir}/iml-device.service

%package journal
Summary: Consumer of cluster journal messages
License: MIT
Group: System Environment/Libraries
Requires: rust-iml-agent-comms

%description journal
%{summary}

%post journal
%systemd_post iml-journal.service

%preun journal
%systemd_preun iml-journal.service

%postun journal
%systemd_postun_with_restart iml-journal.service

%files journal
%{_bindir}/iml-journal
%attr(0644,root,root)%{_unitdir}/iml-journal.service

%package corosync
Summary: Consumer of corosync updates
License: MIT
Group: System Environment/Libraries
Requires: rust-iml-agent-comms

%description corosync
%{summary}

%post corosync
%systemd_post iml-rust-corosync.service

%preun corosync
%systemd_preun iml-rust-corosync.service

%postun corosync
%systemd_postun_with_restart iml-rust-corosync.service

%files corosync
%{_bindir}/iml-corosync
%attr(0644,root,root)%{_unitdir}/iml-rust-corosync.service

%package timer
Summary: Timer service to schedule tasks on specified intervals
License: MIT
Group: System Environment/Libraries

%description timer
%{summary}

%post timer
%systemd_post iml-timer.service

%preun timer
%systemd_preun iml-timer.service

%postun timer
%systemd_postun_with_restart iml-timer.service

%files timer
%{_bindir}/iml-timer
%attr(0644,root,root)%{_unitdir}/iml-timer.service

%changelog
* Thu Dec 10 2020 Will Johnson <wjohnson@whamcloud.com> - 0.5.0-1
- IML Manager 6.3 release

* Thu Sep 17 2020 Will Johnson <wjohnson@whamcloud.com> - 0.3.0-1
- Add timer service

* Wed Sep 18 2019 Will Johnson <wjohnson@whamcloud.com> - 0.2.0-1
- Add ntp service

* Wed Mar 6 2019 Joe Grund <jgrund@whamcloud.com> - 0.1.0-1
- Initial package
