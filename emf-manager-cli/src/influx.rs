// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::EmfManagerCliError;
use emf_cmd::{self, CheckedCommandExt};
use emf_systemd::restart_unit;
use futures::TryFutureExt;
use std::{path::Path, str};
use structopt::StructOpt;
use tokio::fs;

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum Command {
    /// Generate Influx config
    #[structopt(name = "generate-config", setting = structopt::clap::AppSettings::ColoredHelp)]
    GenerateConfig {
        /// Port influx should bind to on startup
        #[structopt(long, env = "INFLUXDB_SERVICE_PORT")]
        bindport: u16,
    },

    /// Start necessary units
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Start,

    /// Setup running influxdb
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Setup {
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
    },
}

pub async fn cli(command: Command) -> Result<(), EmfManagerCliError> {
    match command {
        Command::GenerateConfig { bindport } => {
            generate_config("/etc/default/influxdb", bindport).await
        }
        Command::Start => {
            restart_unit("influxdb.service".to_string())
                .err_into()
                .await
        }
        Command::Setup {
            maindb,
            statdb,
            scandb,
            duration,
        } => {
            influx(None, format!("CREATE DATABASE {}", maindb)).await?;
            influx(None, format!("CREATE DATABASE {}", scandb)).await?;
            influx(
                &scandb,
                format!(
                    r#"ALTER RETENTION POLICY "autogen" ON "{}" DURATION 90d SHARD DURATION 9d"#,
                    scandb
                ),
            )
            .await?;
            influx(None, format!("CREATE DATABASE {}", statdb)).await?;
            let rc = influx(&statdb, format!(r#"CREATE RETENTION POLICY "long_term" ON "{}" DURATION {} REPLICATION 1 SHARD DURATION 5d"#, statdb, duration)).await;
            if rc.is_err() {
                influx(&statdb, format!(r#"ALTER RETENTION POLICY "long_term" ON "{}" DURATION {} REPLICATION 1 SHARD DURATION 5d"#, statdb, duration)).await?;
            }
            let cmd = vec![
                format!(r#"DROP CONTINUOUS QUERY "downsample_means" ON "{}""#, statdb),
                format!(r#"DROP CONTINUOUS QUERY "downsample_lnet" ON "{}""#, statdb),
                format!(r#"DROP CONTINUOUS QUERY "downsample_samples" ON "{}""#, statdb),
                format!(r#"DROP CONTINUOUS QUERY "downsample_sums" ON "{}""#, statdb),
                format!(r#"CREATE CONTINUOUS QUERY "downsample_means" ON "{}" BEGIN SELECT mean(*) INTO "{}"."long_term".:MEASUREMENT FROM "{}"."autogen"."target","{}"."autogen"."host","{}"."autogen"."node" GROUP BY time(30m),* END"#, statdb, statdb, statdb, statdb, statdb),
                format!(r#"CREATE CONTINUOUS QUERY "downsample_lnet" ON "{}" BEGIN SELECT (last("send_count") - first("send_count")) / count("send_count") AS "mean_diff_send", (last("recv_count") - first("recv_count")) / count("recv_count") AS "mean_diff_recv" INTO "{}"."long_term"."lnet" FROM "lnet" WHERE "nid" != '"0@lo"' GROUP BY time(30m),"host","nid" END"#, statdb, statdb),
                format!(r#"CREATE CONTINUOUS QUERY "downsample_samples" ON "{}" BEGIN SELECT (last("samples") - first("samples")) / count("samples") AS "mean_diff_samples" INTO "{}"."long_term"."target" FROM "target" GROUP BY time(30m),* END"#, statdb, statdb),
                format!(r#"CREATE CONTINUOUS QUERY "downsample_sums" ON "{}" BEGIN SELECT (last("sum") - first("sum")) / count("sum") AS "mean_diff_sum" INTO "{}"."long_term"."target" FROM "target" WHERE "units"='"bytes"' GROUP BY time(30m),* END"#, statdb, statdb),
                ].join("; ");
            influx(&statdb, cmd).await?;
            influx(&statdb, format!(r#"ALTER RETENTION POLICY "autogen" ON "{}" DURATION 1d  REPLICATION 1 SHARD DURATION 2h DEFAULT"#, statdb)).await?;
            Ok(())
        }
    }
}

// Disable reporting
// Disable influx http logging (of every write and every query)
async fn generate_config(path: impl AsRef<Path>, bindport: u16) -> Result<(), EmfManagerCliError> {
    fs::write(
        path,
        format!(
            r#"INFLUXDB_DATA_QUERY_LOG_ENABLED=false
INFLUXDB_HTTP_BIND_ADDRESS=127.0.0.1:{}
INFLUXDB_REPORTING_DISABLED=true
INFLUXDB_HTTP_LOG_ENABLED=false
"#,
            bindport
        ),
    )
    .await?;
    Ok(())
}

async fn influx(db: impl Into<Option<&String>>, cmd: String) -> Result<(), EmfManagerCliError> {
    let args = if let Some(db) = db.into() {
        vec!["-database", db, "-execute", &cmd]
    } else {
        vec!["-execute", &cmd]
    };

    emf_cmd::Command::new("influx")
        .args(args)
        .checked_status()
        .err_into()
        .await
}
