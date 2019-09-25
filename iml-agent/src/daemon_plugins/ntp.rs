// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    cmd::cmd_output,
    daemon_plugins::{as_output, DaemonPlugin, Output},
    systemd,
};
use futures::{future, Future, Stream};
use iml_wire_types::ntp::{TimeOffset, TimeStatus, TimeSync};
use lazy_static::lazy_static;
use regex::Regex;
use std::path::Path;
use std::process;
use tracing::{debug, info, warn};

static NTP_CONFIG_FILE: &'static str = "/etc/ntp.conf";

#[derive(Debug)]
pub struct Ntp;

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct SystemdUnit {
    enabled: bool,
    active: bool,
}

#[derive(serde::Serialize, serde::Deserialize, Debug)]
pub struct TimeSyncServices {
    ntpd: SystemdUnit,
    chronyd: SystemdUnit,
}

impl TimeSyncServices {
    fn is_ntp_only(&self) -> bool {
        self.ntpd.enabled && self.ntpd.active && !self.chronyd.enabled && !self.chronyd.active
    }
}

fn is_ntp_synced(output: &str) -> TimeSync {
    let x = match output {
        "b true" => TimeSync::Synced,
        "b false" => TimeSync::Unsynced,
        _ => {
            warn!(
                "is_ntp_synced received {}. Expected either \"b true\" or \"b false\".",
                output
            );
            TimeSync::Unsynced
        }
    };

    debug!("is_ntp_synced: {:?}; equal? {}", x, output == "b true");
    x
}

fn get_ntp_time_offset(output: String) -> Option<TimeOffset> {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"time correct to within (.+)\n").unwrap();
    }

    RE.captures(output.as_ref())
        .and_then(|caps| caps.get(1))
        .map(|x| x.as_str().to_string().into())
}

fn get_chrony_time_offset(output: String) -> Option<TimeOffset> {
    lazy_static! {
        static ref RE: Regex = Regex::new(r"Offset          : [+-](.+)\n").unwrap();
    }

    RE.captures(output.as_ref())
        .and_then(|caps| caps.get(1))
        .map(|x| x.as_str().to_string().into())
}

fn create_time_status((synced, offset): (TimeSync, Option<TimeOffset>)) -> TimeStatus {
    TimeStatus { synced, offset }
}

pub fn create() -> impl DaemonPlugin {
    Ntp
}

fn get_systemd_unit_for_service(
    service: &str,
) -> impl Future<Item = SystemdUnit, Error = ImlAgentError> {
    systemd::systemctl_enabled(service)
        .join(systemd::systemctl_status(service))
        .map(
            |(enabled, active): (std::process::Output, std::process::Output)| SystemdUnit {
                enabled: enabled.status.success(),
                active: active.status.success(),
            },
        )
}

fn is_ntp_configured_by_iml() -> impl Future<Item = bool, Error = ImlAgentError> {
    iml_fs::stream_file_lines(Path::new(NTP_CONFIG_FILE))
        .filter(|l| l.find("# IML_EDIT").is_some())
        .from_err()
        .into_future()
        .map(|(x, _)| x.is_some())
        .map_err(|(e, _)| ImlAgentError::Io(e))
}

fn get_time_sync_services() -> impl Future<Item = TimeSyncServices, Error = ImlAgentError> {
    let ntpd = get_systemd_unit_for_service("ntpd");
    let chronyd = get_systemd_unit_for_service("chronyd");

    ntpd.join(chronyd)
        .map(|(ntpd, chronyd): (SystemdUnit, SystemdUnit)| TimeSyncServices { ntpd, chronyd })
}

fn get_ntpstat_command() -> impl Future<Item = String, Error = ImlAgentError> {
    cmd_output("ntpstat", &[]).map(|p| std::str::from_utf8(&p.stdout).unwrap_or("").to_string())
}

fn get_chronyc_ntpdata_command() -> impl Future<Item = String, Error = ImlAgentError> {
    cmd_output("chronyc", &["ntpdata"])
        .map(|p| std::str::from_utf8(&p.stdout).unwrap_or("").to_string())
}

fn is_ntp_synced_command() -> impl Future<Item = String, Error = ImlAgentError> {
    cmd_output(
        "busctl",
        &[
            "get-property",
            "org.freedesktop.timedate1",
            "/org/freedesktop/timedate1",
            "org.freedesktop.timedate1",
            "NTPSynchronized",
        ],
    )
    .map(|x: process::Output| {
        std::str::from_utf8(&x.stdout)
            .unwrap_or("")
            .trim()
            .to_string()
    })
}

fn ntpd_synced() -> impl Future<Item = TimeStatus, Error = ImlAgentError> {
    let ntp_synced = is_ntp_synced_command().map(|x| is_ntp_synced(&x));
    let time_offset = get_ntpstat_command().map(get_ntp_time_offset);

    ntp_synced.join(time_offset).map(create_time_status)
}

// Gets the output of chronyd
//
// # Arguments
//
// * `x` - The service to check
fn chronyd_synced() -> impl Future<Item = TimeStatus, Error = ImlAgentError> {
    let ntp_synced = is_ntp_synced_command().map(|x| is_ntp_synced(&x));
    let time_offset = get_chronyc_ntpdata_command().map(get_chrony_time_offset);

    Box::new(ntp_synced.join(time_offset).map(create_time_status))
}

fn time_synced<
    F1: Future<Item = bool, Error = ImlAgentError>,
    F2: Future<Item = TimeSyncServices, Error = ImlAgentError>,
    F3: Future<Item = TimeStatus, Error = ImlAgentError>,
    F4: Future<Item = TimeStatus, Error = ImlAgentError>,
>(
    is_ntp_configured_by_iml: fn() -> F1,
    get_time_sync_services: fn() -> F2,
    ntpd_synced: fn() -> F3,
    chronyd_synced: fn() -> F4,
) -> impl Future<Item = Output, Error = ImlAgentError> {
    is_ntp_configured_by_iml()
        .and_then(move |configured| {
            debug!("Configured: {:?}", configured);
            get_time_sync_services().map(move |tss| {
                debug!("time_sync_service shows: {:?}", tss);
                (configured, tss)
            })
        })
        .map(|(configured, tss)| {
            if configured == false || (configured == true && tss.is_ntp_only()) {
                Some(tss)
            } else {
                None
            }
        })
        .and_then(move |tss: Option<TimeSyncServices>| {
            if let Some(tss) = tss {
                // Which one is being used?
                if tss.ntpd.enabled && tss.ntpd.active {
                    future::Either::A(future::Either::A(ntpd_synced()))
                } else {
                    future::Either::A(future::Either::B(chronyd_synced()))
                }
            } else {
                info!("Neither chrony or ntp setup. Setting to unsynced!");
                future::Either::B(future::ok(TimeStatus {
                    synced: TimeSync::Unsynced,
                    offset: None,
                }))
            }
        })
        .and_then(as_output)
        .from_err()
}

impl DaemonPlugin for Ntp {
    fn start_session(&mut self) -> Box<dyn Future<Item = Output, Error = ImlAgentError> + Send> {
        Box::new(time_synced(
            is_ntp_configured_by_iml,
            get_time_sync_services,
            ntpd_synced,
            chronyd_synced,
        ))
    }

    fn update_session(&self) -> Box<dyn Future<Item = Output, Error = ImlAgentError> + Send> {
        Box::new(time_synced(
            is_ntp_configured_by_iml,
            get_time_sync_services,
            ntpd_synced,
            chronyd_synced,
        ))
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_is_ntp_synced() {
        let s: String = r#"b true"#.into();

        assert_eq!(is_ntp_synced(&s), TimeSync::Synced);
    }

    #[test]
    fn test_is_ntp_not_synced() {
        let s: String = r#"b false"#.into();

        assert_eq!(is_ntp_synced(&s), TimeSync::Unsynced);
    }

    #[test]
    fn test_get_ntp_time_offset() {
        let s: String = r#"synchronised to NTP server (10.73.10.10) at stratum 12
time correct to within 949 ms
polling server every 64 s"#
            .into();

        assert_eq!(get_ntp_time_offset(s), Some("949 ms".to_string().into()));
    }

    #[test]
    fn test_get_chrony_time_offset() {
        let s: String = r#"

Remote address  : 10.73.10.10 (0A490A0A)
Remote port     : 123
Local address   : 10.73.10.12 (0A490A0C)
Leap status     : Normal
Version         : 4
Mode            : Server
Stratum         : 11
Poll interval   : 4 (16 seconds)
Precision       : -25 (0.000000030 seconds)
Root delay      : 0.000000 seconds
Root dispersion : 0.011124 seconds
Reference ID    : 7F7F0100 ()
Reference time  : Fri Sep 13 08:03:04 2019
Offset          : +0.000026767 seconds
Peer delay      : 0.000403893 seconds
Peer dispersion : 0.000000056 seconds
Response time   : 0.000079196 seconds
Jitter asymmetry: +0.00
NTP tests       : 111 111 1111
Interleaved     : No
Authenticated   : No
TX timestamping : Kernel
RX timestamping : Kernel
Total TX        : 1129
Total RX        : 1129
Total valid RX  : 1129"#
            .into();

        assert_eq!(
            get_chrony_time_offset(s),
            Some("0.000026767 seconds".to_string().into())
        );
    }

    #[test]
    fn test_session_with_ntp_configured_by_iml() {
        fn is_ntp_configured_by_iml() -> Box<dyn Future<Item = bool, Error = ImlAgentError> + Send>
        {
            println!("TestSideEffect: is ntp configured by iml");
            Box::new(future::ok::<bool, ImlAgentError>(true))
        }

        fn get_time_sync_services(
        ) -> Box<dyn Future<Item = TimeSyncServices, Error = ImlAgentError> + Send> {
            Box::new(future::ok::<TimeSyncServices, ImlAgentError>(
                TimeSyncServices {
                    ntpd: SystemdUnit {
                        enabled: true,
                        active: true,
                    },
                    chronyd: SystemdUnit {
                        enabled: false,
                        active: false,
                    },
                },
            ))
        }

        fn ntpd_synced() -> Box<dyn Future<Item = TimeStatus, Error = ImlAgentError> + Send> {
            Box::new(future::ok::<TimeStatus, ImlAgentError>(create_time_status(
                (TimeSync::Synced, Some("949 ms".to_string().into())),
            )))
        }

        fn chronyd_synced() -> Box<dyn Future<Item = TimeStatus, Error = ImlAgentError> + Send> {
            Box::new(future::ok::<TimeStatus, ImlAgentError>(create_time_status(
                (TimeSync::Unsynced, None),
            )))
        }

        let r = time_synced(
            is_ntp_configured_by_iml,
            get_time_sync_services,
            ntpd_synced,
            chronyd_synced,
        )
        .wait()
        .unwrap();

        assert_eq!(
            r,
            serde_json::to_value(TimeStatus {
                synced: TimeSync::Synced,
                offset: Some("949 ms".to_string().into())
            })
            .ok()
        );
    }
}
