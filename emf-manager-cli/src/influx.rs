// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{display_utils::display_success, error::EmfManagerCliError};
use emf_cmd::{self, CheckedCommandExt};
use emf_systemd::restart_unit;
use futures::TryFutureExt;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum Command {
    /// Start necessary units
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Start,

    /// Setup running influxdb
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Setup(Setup),
}

#[derive(Debug, Default, StructOpt)]
pub struct Setup {
    /// EMF database name
    #[structopt(
        short = "e",
        long = "emfdb",
        default_value = "emf",
        env = "INFLUXDB_EMF_DB"
    )]
    maindb: String,

    /// EMF Stats database name
    #[structopt(
        short = "t",
        long = "statsdb",
        default_value = "emf_stats",
        env = "INFLUXDB_EMF_STATS_DB"
    )]
    statdb: String,

    /// Stratagem Scan database name
    #[structopt(
        short = "c",
        long = "scandb",
        default_value = "emf_stratagem_scans",
        env = "INFLUXDB_STRATAGEM_SCAN_DB"
    )]
    scandb: String,

    /// EMF database name
    #[structopt(
        short = "l",
        long = "long-duration",
        default_value = "52w",
        env = "INFLUXDB_EMF_STATS_LONG_DURATION"
    )]
    duration: String,
}

pub async fn cli(command: Command) -> Result<(), EmfManagerCliError> {
    match command {
        Command::Start => {
            restart_unit("influxdb.service".to_string()).await?;
        }
        Command::Setup(Setup {
            maindb,
            statdb,
            scandb,
            duration,
        }) => {
            println!("Setting up influx...");
            let url = format!(
                "http://{}/ping?wait_for_leader=10s",
                std::env::var("INFLUXDB_HTTP_BIND_ADDRESS").map_err(|_| {
                    EmfManagerCliError::DoesNotExist(
                        "environment variable INFLUXDB_HTTP_BIND_ADDRESS".to_string(),
                    )
                })?
            );
            tracing::debug!("Waiting for influx start (url: {})", &url);
            let mut i: i32 = 30;
            let waitfor = tokio::time::Duration::from_secs(2);
            loop {
                if let Ok(resp) = reqwest::get(&url).await {
                    if resp.status().is_success() {
                        break;
                    }
                }
                if i == 0 {
                    tracing::error!("Influx start up timed out");
                    return Err(EmfManagerCliError::ConfigError(
                        "Failed to start influxdb".to_string(),
                    ));
                }
                tokio::time::sleep(waitfor).await;
                i -= 2;
            }
            tracing::info!("Creating Influx DBs");
            influx(
                None,
                vec![
                    format!("CREATE DATABASE {}", maindb),
                    format!("CREATE DATABASE {}", scandb),
                    format!("CREATE DATABASE {}", statdb),
                ]
                .join("; "),
            )
            .await?;
            influx(
                &scandb,
                format!(
                    r#"ALTER RETENTION POLICY "autogen" ON "{}" DURATION 90d SHARD DURATION 9d"#,
                    scandb
                ),
            )
            .await?;

            let rc = influx(&statdb, format!(r#"CREATE RETENTION POLICY "long_term" ON "{}" DURATION {} REPLICATION 1 SHARD DURATION 5d"#, statdb, duration)).await;
            if rc.is_err() {
                influx(&statdb, format!(r#"ALTER RETENTION POLICY "long_term" ON "{}" DURATION {} REPLICATION 1 SHARD DURATION 5d"#, statdb, duration)).await?;
            }
            let cmd = vec![
                format!(r#"DROP CONTINUOUS QUERY "downsample_means" ON "{}""#, statdb),
                format!(r#"DROP CONTINUOUS QUERY "downsample_lnet" ON "{}""#, statdb),
                format!(r#"DROP CONTINUOUS QUERY "downsample_samples" ON "{}""#, statdb),
                format!(r#"DROP CONTINUOUS QUERY "downsample_sums" ON "{}""#, statdb),
                format!(r#"CREATE CONTINUOUS QUERY "downsample_means" ON "{}" BEGIN SELECT mean(*) INTO "{}"."long_term".:MEASUREMENT FROM "{}"."autogen"."target","{}"."autogen"."host","{}"."autogen"."node","{}"."autogen"."jobstats" GROUP BY time(30m),* END"#, statdb, statdb, statdb, statdb, statdb, statdb),
                format!(r#"CREATE CONTINUOUS QUERY "downsample_lnet" ON "{}" BEGIN SELECT (last("send_count") - first("send_count")) / count("send_count") AS "mean_diff_send", (last("recv_count") - first("recv_count")) / count("recv_count") AS "mean_diff_recv" INTO "{}"."long_term"."lnet" FROM "lnet" WHERE "nid" != '"0@lo"' GROUP BY time(30m),"host","nid" END"#, statdb, statdb),
                format!(r#"CREATE CONTINUOUS QUERY "downsample_samples" ON "{}" BEGIN SELECT (last("samples") - first("samples")) / count("samples") AS "mean_diff_samples" INTO "{}"."long_term"."target" FROM "target" GROUP BY time(30m),* END"#, statdb, statdb),
                format!(r#"CREATE CONTINUOUS QUERY "downsample_sums" ON "{}" BEGIN SELECT (last("sum") - first("sum")) / count("sum") AS "mean_diff_sum" INTO "{}"."long_term"."target" FROM "target" WHERE "units"='"bytes"' GROUP BY time(30m),* END"#, statdb, statdb),
                ].join("; ");
            influx(&statdb, cmd).await?;
            influx(&statdb, format!(r#"ALTER RETENTION POLICY "autogen" ON "{}" DURATION 1d  REPLICATION 1 SHARD DURATION 2h DEFAULT"#, statdb)).await?;
            display_success("Successfully configured influx".to_string());
        }
    }
    Ok(())
}

async fn influx(db: impl Into<Option<&String>>, cmd: String) -> Result<(), EmfManagerCliError> {
    let args = if let Some(db) = db.into() {
        vec!["-database", db, "-execute", &cmd]
    } else {
        vec!["-execute", &cmd]
    };

    // Drop stdout
    let _ = emf_cmd::Command::new("influx")
        .args(args)
        .checked_output()
        .await?;
    Ok(())
}
