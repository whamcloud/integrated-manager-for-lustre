// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlTaskRunnerError;
use bigdecimal::{BigDecimal, ToPrimitive};
use iml_influx::{Client, Point, Points, Precision, Value};
use iml_manager_client::Url;
use iml_manager_env::{get_influxdb_addr, get_influxdb_metrics_db};
use iml_postgres::sqlx::{self, PgPool};
use iml_tracing::tracing;
use std::time::Duration;
use tokio::time;

struct TaskStats {
    actions: Vec<String>,
    filesystem: String,
    fids_total: Option<BigDecimal>,
    fids_completed: Option<BigDecimal>,
    fids_failed: Option<BigDecimal>,
}

const DELAY: Duration = Duration::from_secs(60);

pub(crate) async fn collector(pool: PgPool) -> Result<(), ImlTaskRunnerError> {
    let mut interval = time::interval(DELAY);

    let influx_url: String = format!("http://{}", get_influxdb_addr());
    tracing::debug!("influx_url: {}", &influx_url);

    loop {
        interval.tick().await;

        let stats: Vec<TaskStats> = sqlx::query_as!(
            TaskStats,
            r#"SELECT SUM(fids_total) AS fids_total,
SUM(fids_completed) AS fids_completed,
SUM(fids_failed) AS fids_failed,
actions,
fs.name AS filesystem FROM chroma_core_task AS t
JOIN chroma_core_managedfilesystem AS fs ON t.filesystem_id = fs.id GROUP BY actions,fs.name"#
        )
        .fetch_all(&pool)
        .await?;

        if stats.is_empty() {
            continue;
        }

        let client = Client::new(
            Url::parse(&influx_url).expect("Influx URL is invalid."),
            get_influxdb_metrics_db(),
        );

        let xs = stats
            .iter()
            .filter_map(|stat| {
                if let Some(action) = stat.actions.first() {
                    Some(
                        Point::new("task")
                            .add_tag("action", Value::String(action.to_string()))
                            .add_tag("filesystem", Value::String(stat.filesystem.clone()))
                            .add_field(
                                "fids_completed",
                                Value::Integer(
                                    stat.fids_completed
                                        .as_ref()
                                        .map(|x| x.to_i64())
                                        .flatten()
                                        .unwrap_or(0),
                                ),
                            )
                            .add_field(
                                "fids_failed",
                                Value::Integer(
                                    stat.fids_failed
                                        .as_ref()
                                        .map(|x| x.to_i64())
                                        .flatten()
                                        .unwrap_or(0),
                                ),
                            )
                            .add_field(
                                "fids_total",
                                Value::Integer(
                                    stat.fids_total
                                        .as_ref()
                                        .map(|x| x.to_i64())
                                        .flatten()
                                        .unwrap_or(0),
                                ),
                            ),
                    )
                } else {
                    None
                }
            })
            .collect();
        let points = Points::create_new(xs);

        if let Err(e) = client
            .write_points(points, Some(Precision::Seconds), None)
            .await
        {
            tracing::error!("Error writing series to influxdb: {}", e);
        }
    }
}
