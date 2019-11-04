// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    cmd::cmd_output,
    daemon_plugins::{DaemonPlugin, Output},
    systemd,
};
use futures::{future, Future, StreamExt, TryFutureExt, TryStreamExt};
use iml_wire_types::ntp::{TimeOffset, TimeStatus, TimeSync};
use lazy_static::lazy_static;
use regex::Regex;
use std::pin::Pin;
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

async fn get_systemd_unit_for_service(service: &str) -> Result<SystemdUnit, ImlAgentError> {
    let (enabled, active) = future::try_join(
        systemd::systemctl_enabled(service),
        systemd::systemctl_status(service),
    )
    .await?;

    Ok(SystemdUnit {
        enabled: enabled.status.success(),
        active: active.status.success(),
    })
}

async fn is_ntp_configured_by_iml() -> Result<bool, ImlAgentError> {
    let x = iml_fs::stream_file_lines(NTP_CONFIG_FILE)
        .boxed()
        .try_filter(|l| future::ready(l.find("# IML_EDIT").is_some()))
        .try_next()
        .await?
        .is_some();

    Ok(x)
}

async fn get_time_sync_services() -> Result<TimeSyncServices, ImlAgentError> {
    let ntpd = get_systemd_unit_for_service("ntpd");
    let chronyd = get_systemd_unit_for_service("chronyd");

    let (ntpd, chronyd) = future::try_join(ntpd, chronyd).await?;

    Ok(TimeSyncServices { ntpd, chronyd })
}

async fn get_ntpstat_command() -> Result<String, ImlAgentError> {
    let p = cmd_output("ntpstat", vec![]).await?;

    Ok(std::str::from_utf8(&p.stdout).unwrap_or("").to_string())
}

async fn get_chronyc_ntpdata_command() -> Result<String, ImlAgentError> {
    let p = cmd_output("chronyc", vec!["ntpdata"]).await?;

    Ok(std::str::from_utf8(&p.stdout).unwrap_or("").to_string())
}

async fn is_ntp_synced_command() -> Result<String, ImlAgentError> {
    let x = cmd_output(
        "busctl",
        vec![
            "get-property",
            "org.freedesktop.timedate1",
            "/org/freedesktop/timedate1",
            "org.freedesktop.timedate1",
            "NTPSynchronized",
        ],
    )
    .await?;

    Ok(std::str::from_utf8(&x.stdout)
        .unwrap_or("")
        .trim()
        .to_string())
}

async fn ntpd_synced() -> Result<TimeStatus, ImlAgentError> {
    let ntp_synced = is_ntp_synced_command().map_ok(|x| is_ntp_synced(&x));
    let time_offset = get_ntpstat_command().map_ok(get_ntp_time_offset);

    future::try_join(ntp_synced, time_offset)
        .await
        .map(create_time_status)
}

// Gets the output of chronyd
//
// # Arguments
//
// * `x` - The service to check
async fn chronyd_synced() -> Result<TimeStatus, ImlAgentError> {
    let ntp_synced = is_ntp_synced_command().map_ok(|x| is_ntp_synced(&x));
    let time_offset = get_chronyc_ntpdata_command().map_ok(get_chrony_time_offset);

    future::try_join(ntp_synced, time_offset)
        .await
        .map(create_time_status)
}

async fn time_synced<
    F1: Future<Output = Result<bool, ImlAgentError>>,
    F2: Future<Output = Result<TimeSyncServices, ImlAgentError>>,
    F3: Future<Output = Result<TimeStatus, ImlAgentError>>,
    F4: Future<Output = Result<TimeStatus, ImlAgentError>>,
>(
    is_ntp_configured_by_iml: fn() -> F1,
    get_time_sync_services: fn() -> F2,
    ntpd_synced: fn() -> F3,
    chronyd_synced: fn() -> F4,
) -> Result<Output, ImlAgentError> {
    let configured = is_ntp_configured_by_iml().await?;

    debug!("Configured: {:?}", configured);

    let tss = get_time_sync_services().await?;

    debug!("time_sync_service shows: {:?}", tss);

    let tss = if configured == false || (configured == true && tss.is_ntp_only()) {
        Some(tss)
    } else {
        None
    };

    let x = if let Some(tss) = tss {
        // Which one is being used?
        if tss.ntpd.enabled && tss.ntpd.active {
            ntpd_synced().await?
        } else {
            chronyd_synced().await?
        }
    } else {
        info!("Neither chrony or ntp setup. Setting to unsynced!");

        TimeStatus {
            synced: TimeSync::Unsynced,
            offset: None,
        }
    };

    let x = serde_json::to_value(x).map(Some)?;

    Ok(x)
}

impl DaemonPlugin for Ntp {
    fn start_session(
        &mut self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        Box::pin(time_synced(
            is_ntp_configured_by_iml,
            get_time_sync_services,
            ntpd_synced,
            chronyd_synced,
        ))
    }

    fn update_session(
        &self,
    ) -> Pin<Box<dyn Future<Output = Result<Output, ImlAgentError>> + Send>> {
        Box::pin(time_synced(
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

    #[tokio::test]
    async fn test_session_with_ntp_configured_by_iml() -> Result<(), ImlAgentError> {
        fn is_ntp_configured_by_iml(
        ) -> Pin<Box<dyn Future<Output = Result<bool, ImlAgentError>> + Send>> {
            println!("TestSideEffect: is ntp configured by iml");
            Box::pin(future::ok::<bool, ImlAgentError>(true))
        }

        fn get_time_sync_services(
        ) -> Pin<Box<dyn Future<Output = Result<TimeSyncServices, ImlAgentError>> + Send>> {
            Box::pin(future::ok::<TimeSyncServices, ImlAgentError>(
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

        fn ntpd_synced() -> Pin<Box<dyn Future<Output = Result<TimeStatus, ImlAgentError>> + Send>>
        {
            Box::pin(future::ok::<TimeStatus, ImlAgentError>(create_time_status(
                (TimeSync::Synced, Some("949 ms".to_string().into())),
            )))
        }

        fn chronyd_synced(
        ) -> Pin<Box<dyn Future<Output = Result<TimeStatus, ImlAgentError>> + Send>> {
            Box::pin(future::ok::<TimeStatus, ImlAgentError>(create_time_status(
                (TimeSync::Unsynced, None),
            )))
        }

        let r = time_synced(
            is_ntp_configured_by_iml,
            get_time_sync_services,
            ntpd_synced,
            chronyd_synced,
        )
        .await?;

        assert_eq!(
            r,
            serde_json::to_value(TimeStatus {
                synced: TimeSync::Synced,
                offset: Some("949 ms".to_string().into())
            })
            .ok()
        );

        Ok(())
    }
}
