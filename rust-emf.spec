%{?systemd_requires}
BuildRequires: systemd

# The install directory for the manager
%{?!emf_root: %global emf_root /usr/share/emf}

%global crate emf

%global envoy_version 1.17.1.p0.gd6a4496-1p74.gbb8060d

%global kuma_version 1.1.1-1

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

%global debug_package %{nil}

%prep
%setup -c

%build

%install
mkdir -p %{buildroot}%{_bindir}
cp emf %{buildroot}%{_bindir}
cp emf-action-agent %{buildroot}%{_bindir}
cp emf-agent %{buildroot}%{_bindir}
cp emf-api %{buildroot}%{_bindir}
cp emf-config %{buildroot}%{_bindir}
cp emf-corosync %{buildroot}%{_bindir}
cp emf-device %{buildroot}%{_bindir}
cp emf-host %{buildroot}%{_bindir}
cp emf-journal %{buildroot}%{_bindir}
cp emf-mailbox %{buildroot}%{_bindir}
cp emf-network %{buildroot}%{_bindir}
cp emf-ntp %{buildroot}%{_bindir}
cp emf-ostpool %{buildroot}%{_bindir}
cp emf-report %{buildroot}%{_bindir}
cp emf-state-machine %{buildroot}%{_bindir}
cp emf-sfa %{buildroot}%{_bindir}
cp emf-snapshot %{buildroot}%{_bindir}
cp emf-stats %{buildroot}%{_bindir}
cp emf-task-runner %{buildroot}%{_bindir}
cp emf-warp-drive %{buildroot}%{_bindir}
cp emf-timer %{buildroot}%{_bindir}
cp emf-corosync-agent %{buildroot}%{_bindir}
cp emf-device-agent %{buildroot}%{_bindir}
cp emf-host-agent %{buildroot}%{_bindir}
cp emf-journal-agent %{buildroot}%{_bindir}
cp emf-network-agent %{buildroot}%{_bindir}
cp emf-ntp-agent %{buildroot}%{_bindir}
cp emf-ostpool-agent %{buildroot}%{_bindir}
cp emf-postoffice-agent %{buildroot}%{_bindir}
cp emf-snapshot-agent %{buildroot}%{_bindir}
cp emf-stats-agent %{buildroot}%{_bindir}

mkdir -p %{buildroot}%{_unitdir}
cp emf-api.service %{buildroot}%{_unitdir}
cp emf-rust-corosync.service %{buildroot}%{_unitdir}
cp emf-device.service %{buildroot}%{_unitdir}
cp emf-host.service %{buildroot}%{_unitdir}
cp emf-journal.service %{buildroot}%{_unitdir}
cp emf-mailbox.service %{buildroot}%{_unitdir}
cp emf-network.service %{buildroot}%{_unitdir}
cp emf-ntp.service %{buildroot}%{_unitdir}
cp emf-ostpool.service %{buildroot}%{_unitdir}
cp emf-report.service %{buildroot}%{_unitdir}
cp emf-state-machine.service %{buildroot}%{_unitdir}
cp emf-rust-stats.service %{buildroot}%{_unitdir}
cp emf-sfa.service %{buildroot}%{_unitdir}
cp emf-snapshot.service %{buildroot}%{_unitdir}
cp emf-task-runner.service %{buildroot}%{_unitdir}
cp emf-warp-drive.service %{buildroot}%{_unitdir}
cp emf-timer.service %{buildroot}%{_unitdir}
cp kuma/systemd-units/* %{buildroot}%{_unitdir}
cp emf-agent-units/systemd-units/* %{buildroot}%{_unitdir}

mkdir -p %{buildroot}%{_tmpfilesdir}
cp emf-report.conf %{buildroot}%{_tmpfilesdir}
# cp tmpfiles.conf %{buildroot}%{_tmpfilesdir}/emf-agent.conf
mkdir -p %{buildroot}%{_sysconfdir}/emf/dataplanes/
mkdir -p %{buildroot}%{_sysconfdir}/emf/policies/
cp bootstrap.conf %{buildroot}%{_sysconfdir}/emf/bootstrap.conf
cp embedded.conf %{buildroot}%{_sysconfdir}/emf/embedded.conf
cp kuma/dataplanes/* %{buildroot}%{_sysconfdir}/emf/dataplanes
cp kuma/policies/* %{buildroot}%{_sysconfdir}/emf/policies

mkdir -p %{buildroot}%{_sysconfdir}/bash_completion.d
%{buildroot}%{_bindir}/emf shell-completion bash -e emf -o %{buildroot}%{_sysconfdir}/bash_completion.d/emf
mkdir -p %{buildroot}%{_datadir}/zsh/site-functions
%{buildroot}%{_bindir}/emf shell-completion zsh -e emf -o %{buildroot}%{_datadir}/zsh/site-functions/_emf

install -d -p %{buildroot}%{emf_root}
mkdir -p %{buildroot}%{_sysconfdir}/{nginx/conf,nginx/default}.d
touch %{buildroot}%{_sysconfdir}/nginx/conf.d/emf-gateway.conf
mkdir -p %{buildroot}%{_sysconfdir}/grafana/provisioning/dashboards
mkdir -p %{buildroot}%{_sysconfdir}/grafana/provisioning/datasources
cp -r grafana %{buildroot}%{emf_root}
mv %{buildroot}%{emf_root}/grafana/grafana-emf.ini %{buildroot}%{_sysconfdir}/grafana/
mv %{buildroot}%{emf_root}/grafana/dashboards/emf-dashboards.yaml %{buildroot}%{_sysconfdir}/grafana/provisioning/dashboards
mv %{buildroot}%{emf_root}/grafana/datasources/influxdb-emf-datasource.yml %{buildroot}%{_sysconfdir}/grafana/provisioning/datasources
mkdir -p %{buildroot}%{_unitdir}/grafana-server.service.d/
mv %{buildroot}%{emf_root}/grafana/dropin-emf.conf %{buildroot}%{_unitdir}/grafana-server.service.d/90-emf.conf
mkdir -p %{buildroot}%{_unitdir}/nginx.service.d/
cp nginx/nginx-dropin-emf.conf %{buildroot}%{_unitdir}/nginx.service.d/50-nginx-dropin-emf.conf
cp nginx/emf-gateway.conf.template %{buildroot}%{emf_root}
cp nginx/emf-embedded.conf %{buildroot}%{_unitdir}/nginx.service.d/60-emf-embedded.conf
install -D -m 644 influx/influx-dropin-emf.conf %{buildroot}%{_unitdir}/influxdb.service.d/50-influx-dropin-emf.conf
install -D -m 644 postgres/emf-embedded.conf %{buildroot}%{_unitdir}/postgresql-13.service.d/60-emf-embedded.conf
cp emf-manager-redirect.conf %{buildroot}%{_sysconfdir}/nginx/default.d/emf-manager-redirect.conf

install -m 644 emf-manager.target %{buildroot}%{_unitdir}/


%package bootstrap
Summary: Initial bootstrap.conf used by all services
License: MIT
Group: System Environment/Libraries

%description bootstrap
%{summary}

%files bootstrap
%attr(0644,root,root)%{_sysconfdir}/emf/bootstrap.conf

%package embedded
Summary: Setup for embedded deployments
License: MIT
Group: System Environment/Libraries

%description embedded
%{summary}

%files embedded
%attr(0644,root,root)
%{_unitdir}/postgresql-13.service.d/60-emf-embedded.conf
%{_unitdir}/nginx.service.d/60-emf-embedded.conf
%{_sysconfdir}/emf/embedded.conf

%post embedded
%{_bindir}/systemctl daemon-reload >/dev/null 2>&1 || :

# Manager Services
%package manager
Summary: EMF manager

Requires: emf-sos-plugin >= 2.4.0
Requires: rust-emf-api >= %{version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-cli >= %{version}
Requires: rust-emf-config-cli >= %{version}
Requires: rust-emf-corosync >= %{version}
Requires: rust-emf-device >= %{version}
Requires: rust-emf-grafana >= %{version}
# Requires: rust-emf-gui >= 0.4.0
Requires: rust-emf-host >= %{version}
Requires: rust-emf-influx >= %{version}
Requires: rust-emf-journal >= %{version}
Requires: rust-emf-kuma >= %{version}
Requires: rust-emf-mailbox >= %{version}
Requires: rust-emf-manager-target >= %{version}
Requires: rust-emf-network >= %{version}
Requires: rust-emf-nginx >= %{version}
Requires: rust-emf-ntp >= %{version}
Requires: rust-emf-ostpool >= %{version}
Requires: rust-emf-postgres >= %{version}
Requires: rust-emf-report >= %{version}
Requires: rust-emf-sfa >= %{version}
Requires: rust-emf-snapshot >= %{version}
Requires: rust-emf-state-machine >= %{version}
Requires: rust-emf-stats >= %{version}
Requires: rust-emf-task-runner >= %{version}
Requires: rust-emf-timer >= %{version}
Requires: rust-emf-warp-drive >= %{version}


Obsoletes:      chroma-manager
Provides:       chroma-manager
Obsoletes:      Django-south
Obsoletes:      django-celery
Obsoletes:      django-picklefield
Obsoletes:      django-tastypie
Obsoletes:      python2-django16
Obsoletes:      python2-dse
Obsoletes:      python2-iml-manager-cli
Provides:       python2-iml-manager
Obsoletes:      python2-iml-manager

%description manager
%{summary}

%files manager


%package manager-target
Summary: EMF manager systemd target
License: MIT
Group: System Environment/Libraries

%description manager-target
%{summary}

%files manager-target
%attr(0644,root,root)%{_unitdir}/emf-manager.target


%package kuma
Summary: kuma control-plane
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-postgres >= %{version}
Requires: kuma-cp >= %{kuma_version}
Requires: kuma-ctl >= %{kuma_version}

%description kuma
%{summary}

%preun kuma
%systemd_preun kuma.service

%files kuma
%dir %{_sysconfdir}/emf/policies/
%{_sysconfdir}/emf/policies/*
%{_unitdir}/kuma.service


%package postgres
Summary: postgres and sidecar
License: MIT
Group: System Environment/Libraries
Requires:       getenvoy-envoy = %{envoy_version}
Requires:       kuma-dp >= %{kuma_version}
Requires:       rust-emf-bootstrap >= %{version}
Requires:       rust-emf-config-cli >= %{version}
Requires:       postgresql13-server >= 13.1
Requires:       postgresql13-contrib >= 13.1

%description postgres
%{summary}

%files postgres
%{_unitdir}/emf-postgres-sidecar.service
%{_sysconfdir}/emf/dataplanes/postgres.yml


%package influx
Summary: influxdb and sidecar
License: MIT
Group: System Environment/Libraries
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-config-cli >= %{version}
Requires: influxdb < 2

%description influx
%{summary}

%preun influx
%systemd_preun influxdb.service

%files influx
%{_unitdir}/influxdb.service.d/50-influx-dropin-emf.conf
%{_unitdir}/emf-influx-sidecar.service
%{_sysconfdir}/emf/dataplanes/influx.yml

%post influx
%{_bindir}/systemctl daemon-reload >/dev/null 2>&1 || :


%package grafana
Summary: grafana and sidecar
License: MIT
Group: System Environment/Libraries
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-config-cli >= %{version}
Requires: grafana

%description grafana
%{summary}

%preun grafana
%systemd_preun grafana-server.service

%files grafana
%{_sysconfdir}/grafana/grafana-emf.ini
%{_unitdir}/grafana-server.service.d/90-emf.conf
%attr(0644,root,grafana)%{_sysconfdir}/grafana/provisioning/dashboards/emf-dashboards.yaml
%attr(0674,root,grafana)%{emf_root}/grafana/dashboards/
%attr(0644,root,grafana)%{_sysconfdir}/grafana/provisioning/datasources/influxdb-emf-datasource.yml
%{_unitdir}/emf-grafana-sidecar.service
%{_sysconfdir}/emf/dataplanes/grafana.yml

%post grafana
%{_bindir}/systemctl daemon-reload >/dev/null 2>&1 || :

%package nginx
Summary: nginx gateway and sidecar
License: MIT
Group: System Environment/Libraries
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-grafana >= %{version}
Requires: rust-emf-api >= %{version}
Requires: rust-emf-warp-drive >= %{version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-config-cli >= %{version}
Requires: rust-emf-influx >= %{version}
Requires: nginx >= 1:1.12.2

%description nginx
%{summary}

%preun nginx
%systemd_preun nginx.service

%files nginx
%defattr(-,root,root)
%dir %attr(0755,nginx,nginx)%{emf_root}
%ghost %{_sysconfdir}/nginx/conf.d/emf-gateway.conf
%{_sysconfdir}/nginx/default.d/emf-manager-redirect.conf
%{_unitdir}/nginx.service.d/50-nginx-dropin-emf.conf
%{emf_root}/emf-gateway.conf.template
%{_unitdir}/emf-nginx-sidecar.service
%{_sysconfdir}/emf/dataplanes/nginx.yml


%post nginx
%{_bindir}/systemctl daemon-reload >/dev/null 2>&1 || :


%package cli
Summary: EMF manager CLI
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-bootstrap >= %{version}
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
Requires: rust-emf-bootstrap >= %{version}
Provides: rust-iml-config-cli
Obsoletes: rust-iml-config-cli

%description config-cli
%{summary}

%files config-cli
%{_bindir}/emf-config


%package api
Summary: Standalone Rust API build on warp
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Provides: rust-iml-api
Obsoletes: rust-iml-api

%description api
%{summary}

%preun api
%systemd_preun emf-api.service

%files api
%{_bindir}/emf-api
%attr(0644,root,root)%{_unitdir}/emf-api.service
%{_unitdir}/emf-api-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-api-service.yml


%package ostpool
Summary: Consumer of EMF Agent Ostpool push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-postgres >= %{version}
Provides: rust-iml-ostpool
Obsoletes: rust-iml-ostpool

%description ostpool
%{summary}

%preun ostpool
%systemd_preun emf-ostpool.service

%files ostpool
%{_bindir}/emf-ostpool
%attr(0644,root,root)%{_unitdir}/emf-ostpool.service
%{_unitdir}/emf-ostpool-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-ostpool-service.yml


%package task-runner
Summary: Dispatches and tracks Tasks to Client Workers
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Provides: rust-iml-task-runner
Obsoletes: rust-iml-task-runner

%description task-runner
%{summary}

%preun task-runner
%systemd_preun emf-task-runner.service

%files task-runner
%{_bindir}/emf-task-runner
%attr(0644,root,root)%{_unitdir}/emf-task-runner.service


%package state-machine
Summary: State-machine service
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-postgres >= %{version}

%description state-machine
%{summary}

%preun state-machine
%systemd_preun emf-state-machine.service

%files state-machine
%{_bindir}/emf-state-machine
%attr(0644,root,root)%{_unitdir}/emf-state-machine.service
%{_unitdir}/emf-state-machine-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-state-machine-service.yml


%package stats
Summary: Consumer of EMF stats
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-influx >= %{version}
Provides: rust-iml-stats
Obsoletes: rust-iml-stats

%description stats
%{summary}

%preun stats
%systemd_preun emf-rust-stats.service

%files stats
%{_bindir}/emf-stats
%attr(0644,root,root)%{_unitdir}/emf-rust-stats.service
%{_unitdir}/emf-stats-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-stats-service.yml


%package warp-drive
Summary: Streaming EMF messages with Server-Sent Events
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-postgres >= %{version}
Provides: rust-iml-warp-drive
Obsoletes: rust-iml-warp-drive

%description warp-drive
%{summary}


%preun warp-drive
%systemd_preun emf-warp-drive.service

%files warp-drive
%{_bindir}/emf-warp-drive
%attr(0644,root,root)%{_unitdir}/emf-warp-drive.service
%{_unitdir}/emf-warp-drive-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-warp-drive-service.yml


%package mailbox
Summary: Performs bidirectional streaming of large datasets
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Provides: rust-iml-mailbox
Obsoletes: rust-iml-mailbox

%description mailbox
%{summary}

%preun mailbox
%systemd_preun mailbox.service

%files mailbox
%{_bindir}/emf-mailbox
%attr(0644,root,root)%{_unitdir}/emf-mailbox.service


%package host
Summary: Consumer of EMF Agent Host push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-postgres >= %{version}
Requires: rust-emf-bootstrap >= %{version}

%description host
%{summary}

%preun host
%systemd_preun emf-host.service

%files host
%{_bindir}/emf-host
%attr(0644,root,root)%{_unitdir}/emf-host.service
%{_unitdir}/emf-host-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-host-service.yml


%package network
Summary: Consumer of EMF Agent Network push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-postgres >= %{version}
Requires: rust-emf-influx >= %{version}
Requires: rust-emf-bootstrap >= %{version}
Provides: rust-iml-network
Obsoletes: rust-iml-network

%description network
%{summary}

%preun network
%systemd_preun emf-network.service

%files network
%{_bindir}/emf-network
%attr(0644,root,root)%{_unitdir}/emf-network.service
%{_unitdir}/emf-network-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-network-service.yml


%package ntp
Summary: Consumer of EMF Agent Ntp push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-postgres >= %{version}
Provides: rust-iml-ntp
Obsoletes: rust-iml-ntp

%description ntp
%{summary}

%preun ntp
%systemd_preun emf-ntp.service

%files ntp
%{_bindir}/emf-ntp
%attr(0644,root,root)%{_unitdir}/emf-ntp.service
%{_unitdir}/emf-ntp-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-ntp-service.yml


%package report
Summary: Performs bidirectional streaming of large datasets
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Provides: rust-iml-report
Obsoletes: rust-iml-report

%description report
%{summary}

%preun report
%systemd_preun report.service

%files report
%{_bindir}/emf-report
%attr(0644,root,root)%{_unitdir}/emf-report.service
%attr(0644,root,root)%{_tmpfilesdir}/emf-report.conf


%package sfa
Summary: Consumer of SFA API calls
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-postgres >= %{version}
Provides: rust-iml-sfa
Obsoletes: rust-iml-sfa

%description sfa
%{summary}

%preun sfa
%systemd_preun emf-sfa.service

%files sfa
%{_bindir}/emf-sfa
%attr(0644,root,root)%{_unitdir}/emf-sfa.service


%package snapshot
Summary: Consumer of snapshot listing
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-influx >= %{version}
Requires: rust-emf-postgres >= %{version}
Provides: rust-iml-snapshot
Obsoletes: rust-iml-snapshot

%description snapshot
%{summary}

%preun snapshot
%systemd_preun emf-snapshot.service

%files snapshot
%{_bindir}/emf-snapshot
%attr(0644,root,root)%{_unitdir}/emf-snapshot.service
%{_unitdir}/emf-snapshot-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-snapshot-service.yml


%package device
Summary: Consumer of EMF Agent device push queue
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-postgres >= %{version}
Provides: rust-iml-device
Obsoletes: rust-iml-device

%description device
%{summary}

%preun device
%systemd_preun emf-device.service

%files device
%{_bindir}/emf-device
%attr(0644,root,root)%{_unitdir}/emf-device.service
%attr(0644,root,root)%{_unitdir}/emf-device-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-device-service.yml


%package journal
Summary: Consumer of cluster journal messages
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-postgres >= %{version}
Provides: rust-iml-journal
Obsoletes: rust-iml-journal

%description journal
%{summary}

%preun journal
%systemd_preun emf-journal.service

%files journal
%{_bindir}/emf-journal
%attr(0644,root,root)%{_unitdir}/emf-journal.service
%attr(0644,root,root)%{_unitdir}/emf-journal-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-journal-service.yml


%package corosync
Summary: Consumer of corosync updates
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-postgres >= %{version}
Provides: rust-iml-corosync
Obsoletes: rust-iml-corosync

%description corosync
%{summary}

%preun corosync
%systemd_preun emf-rust-corosync.service

%files corosync
%{_bindir}/emf-corosync
%attr(0644,root,root)%{_unitdir}/emf-rust-corosync.service
%{_unitdir}/emf-corosync-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-corosync-service.yml


%package timer
Summary: Timer service to schedule tasks on specified intervals
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-manager-target >= %{version}
Requires: rust-emf-bootstrap >= %{version}
Provides: rust-iml-timer
Obsoletes: rust-iml-timer

%description timer
%{summary}

%preun timer
%systemd_preun emf-timer.service

%files timer
%{_bindir}/emf-timer
%attr(0644,root,root)%{_unitdir}/emf-timer.service


# Agent Services

%package agent
Summary: EMF Agent CLI
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-bootstrap >= %{version}
Requires: rust-emf-corosync-agent >= %{version}
Requires: rust-emf-device-agent >= %{version}
Requires: rust-emf-host-agent >= %{version}
Requires: rust-emf-journal-agent >= %{version}
Requires: rust-emf-network-agent >= %{version}
Requires: rust-emf-ntp-agent >= %{version}
Requires: rust-emf-ostpool-agent >= %{version}
Requires: rust-emf-postoffice-agent >= %{version}
Requires: rust-emf-snapshot-agent >= %{version}
Requires: rust-emf-stats-agent >= %{version}

Provides: rust-iml-agent
Obsoletes: rust-iml-agent

%description agent
%{summary}

%files agent
%{_bindir}/emf-agent


%package agent-target
Summary: EMF agent systemd target
License: MIT
Group: System Environment/Libraries

%description agent-target
%{summary}

%files agent-target
%attr(0644,root,root)%{_unitdir}/emf-agent.target


%package action-agent
Summary: Action runner
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}

%preun action-agent
%systemd_preun emf-action-agent.service
%systemd_preun emf-action-agent-sidecar.service

%description action-agent
%{summary}

%files action-agent
%{_bindir}/emf-action-agent
%{_unitdir}/emf-action-agent.service
%{_unitdir}/emf-action-agent-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-action-agent.yml


%package corosync-agent
Summary: ships corosync info to the manager
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}

%description corosync-agent
%{summary}

%preun corosync-agent
%systemd_preun emf-corosync-agent.service
%systemd_preun emf-corosync-agent-sidecar.service

%files corosync-agent
%{_bindir}/emf-corosync-agent
%{_unitdir}/emf-corosync-agent.service
%{_unitdir}/emf-corosync-agent-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-corosync-agent.yml


%package device-agent
Summary: ships device info to the manager
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: emf-device-scanner >= 5.1
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Obsoletes: emf-device-scanner-proxy

%description device-agent
%{summary}

%preun device-agent
%systemd_preun emf-device-agent.service
%systemd_preun emf-device-agent-sidecar.service

%files device-agent
%{_bindir}/emf-device-agent
%{_unitdir}/emf-device-agent.service
%{_unitdir}/emf-device-agent-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-device-agent.yml


%package journal-agent
Summary: ships journal info to the manager
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}
Requires: systemd-journal-gateway

%description journal-agent
%{summary}

%preun journal-agent
%systemd_preun emf-journal-agent.service
%systemd_preun emf-journal-agent-sidecar.service

%files journal-agent
%{_bindir}/emf-journal-agent
%{_unitdir}/emf-journal-agent.service
%{_unitdir}/emf-journal-agent-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-journal-agent.yml

%post journal-agent
%systemd_post systemd-journal-gatewayd.socket

%postun journal-agent
%systemd_postun_with_restart systemd-journal-gatewayd.socket


%package host-agent
Summary: ships host info to the manager
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}

%description host-agent
%{summary}

%preun host-agent
%systemd_preun emf-host-agent.service
%systemd_preun emf-host-agent-sidecar.service

%files host-agent
%{_bindir}/emf-host-agent
%{_unitdir}/emf-host-agent.service
%{_unitdir}/emf-host-agent-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-host-agent.yml


%package network-agent
Summary: ships network info to the manager
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}

%description network-agent
%{summary}

%preun network-agent
%systemd_preun emf-network-agent.service
%systemd_preun emf-network-agent-sidecar.service

%files network-agent
%{_bindir}/emf-network-agent
%{_unitdir}/emf-network-agent.service
%{_unitdir}/emf-network-agent-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-network-agent.yml


%package ntp-agent
Summary: ships ntp info to the manager
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}

%description ntp-agent
%{summary}

%preun ntp-agent
%systemd_preun emf-ntp-agent.service
%systemd_preun emf-ntp-agent-sidecar.service

%files ntp-agent
%{_bindir}/emf-ntp-agent
%{_unitdir}/emf-ntp-agent.service
%{_unitdir}/emf-ntp-agent-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-ntp-agent.yml


%package ostpool-agent
Summary: ships ostpool info to the manager
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}

%description ostpool-agent
%{summary}

%preun ostpool-agent
%systemd_preun emf-ostpool-agent.service
%systemd_preun emf-ostpool-agent-sidecar.service

%files ostpool-agent
%{_bindir}/emf-ostpool-agent
%{_unitdir}/emf-ostpool-agent.service
%{_unitdir}/emf-ostpool-agent-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-ostpool-agent.yml


%package postoffice-agent
Summary: ships postoffice info to the manager
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: rust-emf-bootstrap >= %{version}

%description postoffice-agent
%{summary}

%preun postoffice-agent
%systemd_preun emf-postoffice-agent.service
%systemd_preun emf-postoffice-agent-sidecar.service

%files postoffice-agent
%{_bindir}/emf-postoffice-agent
%{_unitdir}/emf-postoffice-agent.service


%package snapshot-agent
Summary: ships snapshot info to the manager
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}

%description snapshot-agent
%{summary}

%preun snapshot-agent
%systemd_preun emf-snapshot-agent.service
%systemd_preun emf-snapshot-agent-sidecar.service

%files snapshot-agent
%{_bindir}/emf-snapshot-agent
%{_unitdir}/emf-snapshot-agent.service
%{_unitdir}/emf-snapshot-agent-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-snapshot-agent.yml


%package stats-agent
Summary: ships stats info to the manager
License: MIT
Group: System Environment/Libraries
Requires: rust-emf-agent-target >= %{version}
Requires: getenvoy-envoy = %{envoy_version}
Requires: kuma-dp >= %{kuma_version}
Requires: rust-emf-bootstrap >= %{version}

%description stats-agent
%{summary}

%preun stats-agent
%systemd_preun emf-stats-agent.service
%systemd_preun emf-stats-agent-sidecar.service

%files stats-agent
%{_bindir}/emf-stats-agent
%{_unitdir}/emf-stats-agent.service
%{_unitdir}/emf-stats-agent-sidecar.service
%{_sysconfdir}/emf/dataplanes/emf-stats-agent.yml


%changelog
* Thu Dec 10 2020 Will Johnson <wjohnson@whamcloud.com> - 0.5.0-1
- EMF Manager 6.3 release

* Thu Sep 17 2020 Will Johnson <wjohnson@whamcloud.com> - 0.3.0-1
- Add timer service

* Wed Sep 18 2019 Will Johnson <wjohnson@whamcloud.com> - 0.2.0-1
- Add ntp service

* Wed Mar 6 2019 Joe Grund <jgrund@whamcloud.com> - 0.1.0-1
- Initial package
