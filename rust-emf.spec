%{?systemd_requires}
BuildRequires: systemd

%global crate emf

Name: rust-%{crate}
Version: 0.5.0
# Release Start
Release: 1%{?dist}
# Release End
Summary: EXAScaler Management Framework Services

License: MIT

URL: https://github.com/whamcloud/exascaler-management-framework
Source0: rust-core.tar.gz

ExclusiveArch: x86_64

%description
%{summary}

%prep
%setup -c

%build

%install
mkdir -p %{buildroot}%{_bindir}
cp emf %{buildroot}%{_bindir}
cp emf-action-runner %{buildroot}%{_bindir}
cp emf-agent %{buildroot}%{_bindir}
cp emf-agent-comms %{buildroot}%{_bindir}
cp emf-agent-daemon %{buildroot}%{_bindir}
cp emf-api %{buildroot}%{_bindir}
cp emf-config %{buildroot}%{_bindir}
cp emf-corosync %{buildroot}%{_bindir}
cp emf-device %{buildroot}%{_bindir}
cp emf-journal %{buildroot}%{_bindir}
cp emf-mailbox %{buildroot}%{_bindir}
cp emf-network %{buildroot}%{_bindir}
cp emf-ntp %{buildroot}%{_bindir}
cp emf-ostpool %{buildroot}%{_bindir}
cp emf-postoffice %{buildroot}%{_bindir}
cp emf-report %{buildroot}%{_bindir}
cp emf-sfa %{buildroot}%{_bindir}
cp emf-snapshot %{buildroot}%{_bindir}
cp emf-stats %{buildroot}%{_bindir}
cp emf-task-runner %{buildroot}%{_bindir}
cp emf-warp-drive %{buildroot}%{_bindir}
cp emf-timer %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_unitdir}
cp emf-action-runner.{socket,service} %{buildroot}%{_unitdir}
cp emf-agent-comms.service %{buildroot}%{_unitdir}
cp emf-api.service %{buildroot}%{_unitdir}
cp emf-rust-corosync.service %{buildroot}%{_unitdir}
cp emf-device.service %{buildroot}%{_unitdir}
cp emf-journal.service %{buildroot}%{_unitdir}
cp emf-mailbox.service %{buildroot}%{_unitdir}
cp emf-network.service %{buildroot}%{_unitdir}
cp emf-ntp.service %{buildroot}%{_unitdir}
cp emf-ostpool.service %{buildroot}%{_unitdir}
cp emf-postoffice.service %{buildroot}%{_unitdir}
cp emf-report.service %{buildroot}%{_unitdir}
cp emf-rust-stats.service %{buildroot}%{_unitdir}
cp emf-sfa.service %{buildroot}%{_unitdir}
cp emf-snapshot.service %{buildroot}%{_unitdir}
cp emf-task-runner.service %{buildroot}%{_unitdir}
cp emf-warp-drive.service %{buildroot}%{_unitdir}
cp emf-timer.service %{buildroot}%{_unitdir}
cp rust-emf-agent.{service,path} %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_tmpfilesdir}
cp emf-report.conf %{buildroot}%{_tmpfilesdir}
cp tmpfiles.conf %{buildroot}%{_tmpfilesdir}/emf-agent.conf
mkdir -p %{buildroot}%{_presetdir}
cp 00-rust-emf-agent.preset %{buildroot}%{_presetdir}
mkdir -p %{buildroot}%{_sysconfdir}/emf/
cp settings.conf %{buildroot}%{_sysconfdir}/emf/emf-agent.conf
mkdir -p %{buildroot}%{_sysconfdir}/bash_completion.d
%{buildroot}%{_bindir}/emf shell-completion bash -e emf -o %{buildroot}%{_sysconfdir}/bash_completion.d/emf
mkdir -p %{buildroot}%{_datadir}/zsh/site-functions
%{buildroot}%{_bindir}/emf shell-completion zsh -e emf -o %{buildroot}%{_datadir}/zsh/site-functions/_emf

%package cli
Summary: EMF manager CLI
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-cli
Obsoletes: rust-iml-cli

%description cli
%{summary}

%files cli
%{_bindir}/emf

%package cli-bash-completion
Summary: EMF manager CLI (bash completion script)
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-cli-bash-completion
Obsoletes: rust-iml-cli-bash-completion

%description cli-bash-completion
%{summary}

%files cli-bash-completion
%{_sysconfdir}/bash_completion.d/emf

%package cli-zsh-completion
Summary: EMF manager CLI (zsh completion script)
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-cli-zsh-completion
Obsoletes: rust-iml-cli-zsh-completion

%description cli-zsh-completion
%{summary}

%files cli-zsh-completion
%{_datadir}/zsh/site-functions/_emf

%package config-cli
Summary: EMF manager Config CLI
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-config-cli
Obsoletes: rust-iml-config-cli

%description config-cli
%{summary}

%files config-cli
%{_bindir}/emf-config

%package agent
Summary: EMF Agent Daemon and CLI
License: MIT
Group: System Environment/Libraries
Requires: systemd-journal-gateway
Requires: emf-device-scanner >= 5.1
Obsoletes: emf-device-scanner-proxy
Provides: rust-iml-agent
Obsoletes: rust-iml-agent

%description agent
%{summary}

%files agent
%{_bindir}/emf-agent
%{_bindir}/emf-agent-daemon
%attr(0644,root,root)
%{_sysconfdir}/emf/emf-agent.conf
%{_unitdir}/rust-emf-agent.service
%{_unitdir}/rust-emf-agent.path
%{_presetdir}/00-rust-emf-agent.preset
%{_tmpfilesdir}/emf-agent.conf

%post agent
%systemd_post rust-emf-agent.path
%systemd_post systemd-journal-gatewayd.socket
%tmpfiles_create %{_tmpfilesdir}/emf-agent.conf

%preun agent
%systemd_preun rust-emf-agent.path
%systemd_preun rust-emf-agent.service

%postun agent
%systemd_postun_with_restart rust-emf-agent.path
%systemd_postun_with_restart systemd-journal-gatewayd.socket

%package agent-comms
Summary: Communicates with emf-agents
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-agent-comms
Obsoletes: rust-iml-agent-comms

%description agent-comms
%{summary}

%post agent-comms
%systemd_post emf-agent-comms.service

%preun agent-comms
%systemd_preun emf-agent-comms.service

%postun agent-comms
%systemd_postun_with_restart emf-agent-comms.service

%files agent-comms
%{_bindir}/emf-agent-comms
%attr(0644,root,root)%{_unitdir}/emf-agent-comms.service

%package api
Summary: Standalone Rust API build on warp
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-api
Obsoletes: rust-iml-api

%description api
%{summary}

%post api
%systemd_post emf-api.service

%preun api
%systemd_preun emf-api.service

%postun api
%systemd_postun_with_restart emf-api.service

%files api
%{_bindir}/emf-api
%attr(0644,root,root)%{_unitdir}/emf-api.service

%package action-runner
Summary: Dispatches and tracks RPCs to agents
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-action-runner
Obsoletes: rust-iml-action-runner

%description action-runner
%{summary}

%post action-runner
%systemd_post emf-action-runner.socket
%systemd_post emf-action-runner.service

%preun action-runner
%systemd_preun emf-action-runner.socket
%systemd_preun emf-action-runner.service

%postun action-runner
%systemd_postun_with_restart emf-action-runner.socket
%systemd_postun_with_restart emf-action-runner.service

%files action-runner
%{_bindir}/emf-action-runner
%attr(0644,root,root)%{_unitdir}/emf-action-runner.socket
%attr(0644,root,root)%{_unitdir}/emf-action-runner.service

%package ostpool
Summary: Consumer of EMF Agent Ostpool push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-comms
Provides: rust-iml-ostpool
Obsoletes: rust-iml-ostpool

%description ostpool
%{summary}

%post ostpool
%systemd_post emf-ostpool.service

%preun ostpool
%systemd_preun emf-ostpool.service

%postun ostpool
%systemd_postun_with_restart emf-ostpool.service

%files ostpool
%{_bindir}/emf-ostpool
%attr(0644,root,root)%{_unitdir}/emf-ostpool.service

%package task-runner
Summary: Dispatches and tracks Tasks to Client Workers
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-task-runner
Obsoletes: rust-iml-task-runner

%description task-runner
%{summary}

%post task-runner
%systemd_post emf-task-runner.service

%preun task-runner
%systemd_preun emf-task-runner.service

%postun task-runner
%systemd_postun_with_restart emf-task-runner.service

%files task-runner
%{_bindir}/emf-task-runner
%attr(0644,root,root)%{_unitdir}/emf-task-runner.service

%package stats
Summary: Consumer of EMF stats
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-comms
Provides: rust-iml-stats
Obsoletes: rust-iml-stats

%description stats
%{summary}

%post stats
%systemd_post emf-rust-stats.service

%preun stats
%systemd_preun emf-rust-stats.service

%postun stats
%systemd_postun_with_restart emf-rust-stats.service

%files stats
%{_bindir}/emf-stats
%attr(0644,root,root)%{_unitdir}/emf-rust-stats.service

%package warp-drive
Summary: Streaming EMF messages with Server-Sent Events
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-stats
Obsoletes: rust-iml-stats

%description warp-drive
%{summary}

%post warp-drive
%systemd_post emf-warp-drive.service

%preun warp-drive
%systemd_preun emf-warp-drive.service

%postun warp-drive
%systemd_postun_with_restart emf-warp-drive.service

%files warp-drive
%{_bindir}/emf-warp-drive
%attr(0644,root,root)%{_unitdir}/emf-warp-drive.service

%package mailbox
Summary: Performs bidirectional streaming of large datasets
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-mailbox
Obsoletes: rust-iml-mailbox

%description mailbox
%{summary}

%post mailbox
%systemd_post emf-mailbox.service

%preun mailbox
%systemd_preun mailbox.service

%postun mailbox
%systemd_postun_with_restart mailbox.service

%files mailbox
%{_bindir}/emf-mailbox
%attr(0644,root,root)%{_unitdir}/emf-mailbox.service

%package network
Summary: Consumer of EMF Agent Network push queue
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-network
Obsoletes: rust-iml-network

%description network
%{summary}

%post network
%systemd_post emf-network.service

%preun network
%systemd_preun emf-network.service

%postun network
%systemd_postun_with_restart emf-network.service

%files network
%{_bindir}/emf-network
%attr(0644,root,root)%{_unitdir}/emf-network.service

%package ntp
Summary: Consumer of EMF Agent Ntp push queue
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-ntp
Obsoletes: rust-iml-ntp

%description ntp
%{summary}

%post ntp
%systemd_post emf-ntp.service

%preun ntp
%systemd_preun emf-ntp.service

%postun ntp
%systemd_postun_with_restart emf-ntp.service

%files ntp
%{_bindir}/emf-ntp
%attr(0644,root,root)%{_unitdir}/emf-ntp.service

%package postoffice
Summary: Consumer of EMF Agent Postoffice push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-comms
Provides: rust-iml-postoffice
Obsoletes: rust-iml-postoffice

%description postoffice
%{summary}

%post postoffice
%systemd_post emf-postoffice.service

%preun postoffice
%systemd_preun emf-postoffice.service

%postun postoffice
%systemd_postun_with_restart emf-postoffice.service

%files postoffice
%{_bindir}/emf-postoffice
%attr(0644,root,root)%{_unitdir}/emf-postoffice.service

%package report
Summary: Performs bidirectional streaming of large datasets
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-report
Obsoletes: rust-iml-report

%description report
%{summary}

%post report
%systemd_post emf-report.service

%preun report
%systemd_preun report.service

%postun report
%systemd_postun_with_restart report.service

%files report
%{_bindir}/emf-report
%attr(0644,root,root)%{_unitdir}/emf-report.service
%attr(0644,root,root)%{_tmpfilesdir}/emf-report.conf

%package sfa
Summary: Consumer of SFA API calls
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-sfa
Obsoletes: rust-iml-sfa

%description sfa
%{summary}

%post sfa
%systemd_post emf-sfa.service

%preun sfa
%systemd_preun emf-sfa.service

%postun sfa
%systemd_postun_with_restart emf-sfa.service

%files sfa
%{_bindir}/emf-sfa
%attr(0644,root,root)%{_unitdir}/emf-sfa.service

%package snapshot
Summary: Consumer of snapshot listing
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-comms
Provides: rust-iml-snapshot
Obsoletes: rust-iml-snapshot

%description snapshot
%{summary}

%post snapshot
%systemd_post emf-snapshot.service

%preun snapshot
%systemd_preun emf-snapshot.service

%postun snapshot
%systemd_postun_with_restart emf-snapshot.service

%files snapshot
%{_bindir}/emf-snapshot
%attr(0644,root,root)%{_unitdir}/emf-snapshot.service

%package device
Summary: Consumer of EMF Agent device push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-comms
Provides: rust-iml-device
Obsoletes: rust-iml-device

%description device
%{summary}

%post device
%systemd_post emf-device.service

%preun device
%systemd_preun emf-device.service

%postun device
%systemd_postun_with_restart emf-device.service

%files device
%{_bindir}/emf-device
%attr(0644,root,root)%{_unitdir}/emf-device.service

%package journal
Summary: Consumer of cluster journal messages
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-comms
Provides: rust-iml-journal
Obsoletes: rust-iml-journal

%description journal
%{summary}

%post journal
%systemd_post emf-journal.service

%preun journal
%systemd_preun emf-journal.service

%postun journal
%systemd_postun_with_restart emf-journal.service

%files journal
%{_bindir}/emf-journal
%attr(0644,root,root)%{_unitdir}/emf-journal.service

%package corosync
Summary: Consumer of corosync updates
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-comms
Provides: rust-iml-corosync
Obsoletes: rust-iml-corosync

%description corosync
%{summary}

%post corosync
%systemd_post emf-rust-corosync.service

%preun corosync
%systemd_preun emf-rust-corosync.service

%postun corosync
%systemd_postun_with_restart emf-rust-corosync.service

%files corosync
%{_bindir}/emf-corosync
%attr(0644,root,root)%{_unitdir}/emf-rust-corosync.service

%package timer
Summary: Timer service to schedule tasks on specified intervals
License: MIT
Group: System Environment/Libraries
Provides: rust-iml-timer
Obsoletes: rust-iml-timer

%description timer
%{summary}

%post timer
%systemd_post emf-timer.service

%preun timer
%systemd_preun emf-timer.service

%postun timer
%systemd_postun_with_restart emf-timer.service

%files timer
%{_bindir}/emf-timer
%attr(0644,root,root)%{_unitdir}/emf-timer.service

%changelog
* Thu Dec 10 2020 Will Johnson <wjohnson@whamcloud.com> - 0.5.0-1
- EMF Manager 6.3 release

* Thu Sep 17 2020 Will Johnson <wjohnson@whamcloud.com> - 0.3.0-1
- Add timer service

* Wed Sep 18 2019 Will Johnson <wjohnson@whamcloud.com> - 0.2.0-1
- Add ntp service

* Wed Mar 6 2019 Joe Grund <jgrund@whamcloud.com> - 0.1.0-1
- Initial package
