// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::stream::TryStreamExt;
use iml_influx::{Client, Point, Points, Precision, Value};
use iml_manager_env::{get_influxdb_addr, get_influxdb_metrics_db};
use iml_service_queue::service_queue::consume_data;
use iml_stats::error::ImlStatsError;
use iml_wire_types::Fqdn;
use lustre_collector::{
    HostStats, LNetStats, NodeStats, Record, Target, TargetStats,
    {
        types::{BrwStats, TargetVariant},
        Stat, TargetStat,
    },
};
use url::Url;

fn build_stats_query(x: &TargetStat<Vec<Stat>>, stat: &Stat, query: Point) -> Point {
    let mut q = query;
    if x.kind != TargetVariant::MGT {
        q = q.add_tag("fs", Value::String(fs_name(&x.target).to_string()));
    }

    if let Some(min) = stat.min {
        q = q.add_field("min", Value::Integer(min as i64));
        tracing::debug!("Target Stat - min: {}", min);
    }

    if let Some(max) = stat.max {
        q = q.add_field("max", Value::Integer(max as i64));
        tracing::debug!("Target Stat - max: {}", max);
    }

    if let Some(sum) = stat.sum {
        q = q.add_field("sum", Value::Integer(sum as i64));
        tracing::debug!("Target Stat - sum: {}", sum);
    }

    if let Some(sumsquare) = stat.sumsquare {
        q = q.add_field("sumsquare", Value::Integer(sumsquare as i64));
        tracing::debug!("Target Stat - sumsquare: {}", sumsquare);
    }

    q
}

fn handle_stats_record(x: TargetStat<Vec<Stat>>, host: &Fqdn) -> Option<Vec<Point>> {
    tracing::debug!("Stats: {:?}", x);
    Some(
        x.value
            .iter()
            .map(|stat| {
                let mut query = Point::new("target")
                    .add_tag("host", Value::String(host.0.to_string()))
                    .add_tag("target", Value::String(x.target.to_string()))
                    .add_tag("kind", Value::String(x.kind.to_string()))
                    .add_tag("name", Value::String(stat.name.to_string()))
                    .add_tag("units", Value::String(stat.units.to_string()))
                    .add_field("samples", Value::Integer(stat.samples as i64));

                query = build_stats_query(&x, stat, query);

                tracing::debug!(
                    "Target Stats: target: {:?}, name: {}, units: {}",
                    &*x.target,
                    &*stat.name,
                    &*stat.units
                );

                query
            })
            .collect(),
    )
}

fn handle_brw_stats(x: TargetStat<Vec<BrwStats>>, host: &Fqdn) -> Option<Vec<Point>> {
    tracing::debug!("BrwStats: {:?}", x);
    Some(
    x.value
        .iter()
        .flat_map(|brw_stat| {
            brw_stat
                .buckets
                .iter()
                .map(|bucket| {
                    let mut query = Point::new("target")
                        .add_tag("host", Value::String(host.0.to_string()))
                        .add_tag("target", Value::String(x.target.to_string()))
                        .add_tag("kind", Value::String(x.kind.to_string()))
                        .add_tag("name", Value::String(brw_stat.name.to_string()))
                        .add_tag("unit", Value::String(brw_stat.unit.to_string()))
                        .add_tag("bucket_name", Value::Integer(bucket.name as i64))
                        .add_field("read", Value::Integer(bucket.read as i64))
                        .add_field("write", Value::Integer(bucket.write as i64));

                    if x.kind != TargetVariant::MGT {
                        query = query.add_tag("fs", Value::String(fs_name(&x.target).to_string()));
                    }

                    tracing::debug!(
                        "BrwStat: target: {:?}, name: {}, unit: {}, bucket_name: {}, read: {}, write: {}",
                        &*x.target,
                        &*brw_stat.name,
                        &*brw_stat.unit,
                        bucket.name,
                        bucket.read,
                        bucket.write
                    );
                    query
                })
                .collect::<Vec<_>>()
        })
        .collect(),
)
}

fn handle_target_records(target_stats: TargetStats, host: &Fqdn) -> Option<Vec<Point>> {
    match target_stats {
        TargetStats::Stats(x) => handle_stats_record(x, &host),
        TargetStats::BrwStats(x) => handle_brw_stats(x, &host),
        TargetStats::FilesFree(x) => {
            tracing::debug!("FilesFree - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("fs", Value::String(fs_name(&x.target).to_string()))
                .add_field("files_free", Value::Integer(x.value as i64))])
        }
        TargetStats::FilesTotal(x) => {
            tracing::debug!("FilesTotal - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_tag("fs", Value::String(fs_name(&x.target).to_string()))
                .add_field("files_total", Value::Integer(x.value as i64))])
        }
        TargetStats::FsType(x) => {
            tracing::debug!("FsType - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("fs_type", Value::String(x.value))])
        }
        TargetStats::BytesAvail(x) => {
            tracing::debug!("BytesAvail - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_tag("fs", Value::String(fs_name(&x.target).to_string()))
                .add_field("bytes_avail", Value::Integer(x.value as i64))])
        }
        TargetStats::BytesFree(x) => {
            tracing::debug!("BytesFree - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_tag("fs", Value::String(fs_name(&x.target).to_string()))
                .add_field("bytes_free", Value::Integer(x.value as i64))])
        }
        TargetStats::BytesTotal(x) => {
            tracing::debug!("BytesTotal - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_tag("fs", Value::String(fs_name(&x.target).to_string()))
                .add_field("bytes_total", Value::Integer(x.value as i64))])
        }
        TargetStats::NumExports(x) => {
            tracing::debug!("NumExports - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("num_exports", Value::Integer(x.value as i64))])
        }
        TargetStats::TotDirty(x) => {
            tracing::debug!("TotDirty - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("tot_dirty", Value::Integer(x.value as i64))])
        }
        TargetStats::TotGranted(x) => {
            tracing::debug!("TotGranted - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("tot_granted", Value::Integer(x.value as i64))])
        }
        TargetStats::TotPending(x) => {
            tracing::debug!("TotPending - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("tot_pending", Value::Integer(x.value as i64))])
        }
        TargetStats::ContendedLocks(x) => {
            tracing::debug!("ContendedLocks - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field(
                    "contended_locks",
                    Value::Integer(x.value as i64),
                )])
        }
        TargetStats::ContentionSeconds(x) => {
            tracing::debug!("ContentionSeconds - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field(
                    "contention_seconds",
                    Value::Integer(x.value as i64),
                )])
        }
        TargetStats::CtimeAgeLimit(x) => {
            tracing::debug!("CtimeAgeLimit - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field(
                    "ctime_age_limit",
                    Value::Integer(x.value as i64),
                )])
        }
        TargetStats::EarlyLockCancel(x) => {
            tracing::debug!("EarlyLockCancel - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field(
                    "early_lock_cancel",
                    Value::Integer(x.value as i64),
                )])
        }
        TargetStats::LockCount(x) => {
            tracing::debug!("TargetStats - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_tag("fs", Value::String(fs_name(&x.target).to_string()))
                .add_field("lock_count", Value::Integer(x.value as i64))])
        }
        TargetStats::LockTimeouts(x) => {
            tracing::debug!("LockTimeouts - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("lock_timeouts", Value::Integer(x.value as i64))])
        }
        TargetStats::LockUnusedCount(x) => {
            tracing::debug!("LockUnusedCount - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field(
                    "lock_unused_count",
                    Value::Integer(x.value as i64),
                )])
        }
        TargetStats::LruMaxAge(x) => {
            tracing::debug!("LruMaxAge - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("lru_max_age", Value::Integer(x.value as i64))])
        }
        TargetStats::LruSize(x) => {
            tracing::debug!("LruSize - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("lru_size", Value::Integer(x.value as i64))])
        }
        TargetStats::MaxNolockBytes(x) => {
            tracing::debug!("MaxNolockBytes - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field(
                    "max_no_lock_bytes",
                    Value::Integer(x.value as i64),
                )])
        }
        TargetStats::MaxParallelAst(x) => {
            tracing::debug!("MaxParallelAst - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field(
                    "max_parallel_ast",
                    Value::Integer(x.value as i64),
                )])
        }
        TargetStats::ResourceCount(x) => {
            tracing::debug!("ResourceCount - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("resource_count", Value::Integer(x.value as i64))])
        }
        TargetStats::ThreadsMin(x) => {
            tracing::debug!("ThreadsMin - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("threads_min", Value::Integer(x.value as i64))])
        }
        TargetStats::ThreadsMax(x) => {
            tracing::debug!("ThreadsMax - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field("threads_max", Value::Integer(x.value as i64))])
        }
        TargetStats::ThreadsStarted(x) => {
            tracing::debug!("ThreadsStarted - {:?}", x);
            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_field(
                    "threads_started",
                    Value::Integer(x.value as i64),
                )])
        }
        TargetStats::ConnectedClients(x) => {
            tracing::debug!("ConnectedClients - {:?}", x);

            Some(vec![Point::new("target")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("kind", Value::String(x.kind.to_string()))
                .add_tag("target", Value::String(x.target.to_string()))
                .add_tag("fs", Value::String(fs_name(&x.target).to_string()))
                .add_field(
                    "connected_clients",
                    Value::Integer(x.value as i64),
                )])
        }
        TargetStats::FsNames(x) => {
            tracing::warn!(data = ?x, "Unexpected MGS fses");

            None
        }
        TargetStats::JobStatsOst(_) => {
            // Not storing jobstats... yet.
            None
        }
    }
}

fn handle_host_records(host_stats: HostStats, host: &Fqdn) -> Option<Vec<Point>> {
    match host_stats {
        HostStats::MemusedMax(x) => {
            tracing::debug!("MemusedMax - {:?}", x);
            Some(vec![Point::new("host")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_field("memused_max", Value::Integer(x.value as i64))])
        }
        HostStats::Memused(x) => {
            tracing::debug!("Memused - {:?}", x);
            Some(vec![Point::new("host")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_field("memused", Value::Integer(x.value as i64))])
        }
        HostStats::LNetMemUsed(x) => {
            tracing::debug!("LNetMemUsed - {:?}", x);
            Some(vec![Point::new("host")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_field("lnet_mem_used", Value::Integer(x.value as i64))])
        }
        HostStats::HealthCheck(x) => {
            tracing::debug!("HealthCheck - {:?}", x);
            Some(vec![Point::new("host")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_field("health_check", Value::String(x.value))])
        }
    }
}

fn handle_lnet_stat(lnet_stats: LNetStats, host: &Fqdn) -> Option<Vec<Point>> {
    match lnet_stats {
        LNetStats::SendCount(x) => {
            tracing::debug!("SendCount - {:?}", x);
            Some(vec![Point::new("lnet")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("nid", Value::String(x.nid))
                .add_field("send_count", Value::Integer(x.value as i64))])
        }
        LNetStats::RecvCount(x) => {
            tracing::debug!("RecvCount - {:?}", x);
            Some(vec![Point::new("lnet")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("nid", Value::String(x.nid))
                .add_field("recv_count", Value::Integer(x.value as i64))])
        }
        LNetStats::DropCount(x) => {
            tracing::debug!("DropCount - {:?}", x);
            Some(vec![Point::new("lnet")
                .add_tag("host", Value::String(host.0.to_string()))
                .add_tag("nid", Value::String(x.nid))
                .add_field("drop_count", Value::Integer(x.value as i64))])
        }
    }
}

fn handle_node(node: NodeStats, host: &Fqdn) -> Option<Vec<Point>> {
    match node {
        NodeStats::CpuUser(x) => Some(vec![Point::new("node")
            .add_tag("host", Value::String(host.0.to_string()))
            .add_field("cpu_user", Value::Integer(x.value as i64))]),
        NodeStats::CpuSystem(x) => Some(vec![Point::new("node")
            .add_tag("host", Value::String(host.0.to_string()))
            .add_field("cpu_system", Value::Integer(x.value as i64))]),
        NodeStats::CpuIowait(x) => Some(vec![Point::new("node")
            .add_tag("host", Value::String(host.0.to_string()))
            .add_field("cpu_iowait", Value::Integer(x.value as i64))]),
        NodeStats::CpuTotal(x) => Some(vec![Point::new("node")
            .add_tag("host", Value::String(host.0.to_string()))
            .add_field("cpu_total", Value::Integer(x.value as i64))]),
        NodeStats::MemTotal(x) => Some(vec![Point::new("node")
            .add_tag("host", Value::String(host.0.to_string()))
            .add_field("mem_total", Value::Integer(x.value as i64))]),
        NodeStats::MemFree(x) => Some(vec![Point::new("node")
            .add_tag("host", Value::String(host.0.to_string()))
            .add_field("mem_free", Value::Integer(x.value as i64))]),
        NodeStats::SwapTotal(x) => Some(vec![Point::new("node")
            .add_tag("host", Value::String(host.0.to_string()))
            .add_field("swap_total", Value::Integer(x.value as i64))]),
        NodeStats::SwapFree(x) => Some(vec![Point::new("node")
            .add_tag("host", Value::String(host.0.to_string()))
            .add_field("swap_free", Value::Integer(x.value as i64))]),
    }
}

#[tokio::main]
async fn main() -> Result<(), ImlStatsError> {
    iml_tracing::init();

    let pool = iml_rabbit::connect_to_rabbit(1);

    let conn = iml_rabbit::get_conn(pool).await?;

    let ch = iml_rabbit::create_channel(&conn).await?;

    let mut s = consume_data::<Vec<Record>>(&ch, "rust_agent_stats_rx");
    let influx_url: String = format!("http://{}", get_influxdb_addr());
    tracing::debug!("influx_url: {}", &influx_url);

    while let Some((host, xs)) = s.try_next().await? {
        tracing::debug!("Incoming stats: {}: {:?}", host, xs);
        tracing::debug!("host: {:?}", host.0);

        let client = Client::new(
            Url::parse(&influx_url).expect("Influx URL is invalid."),
            get_influxdb_metrics_db(),
        );

        let entries: Vec<_> = xs
            .into_iter()
            .filter_map(|record| match record {
                Record::Target(target_stats) => handle_target_records(target_stats, &host),
                Record::Host(host_stats) => handle_host_records(host_stats, &host),
                Record::LNetStat(lnet_stats) => handle_lnet_stat(lnet_stats, &host),
                Record::Node(node) => handle_node(node, &host),
            })
            .flatten()
            .collect();

        if !entries.is_empty() {
            let points = Points::create_new(entries);

            tracing::debug!("Points: {:?}", points);

            let r = client
                .write_points(points, Some(Precision::Nanoseconds), None)
                .await;

            tracing::debug!("Processed insertions for: {:?}", host);

            if let Err(e) = r {
                tracing::error!("Error writing series to influxdb: {}", e);
            }
        }
    }

    Ok(())
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct MgsFsTime {
    time: u64,
    mgs_fs: String,
    mgs_fs_count: Option<u32>,
}

fn fs_name(t: &Target) -> &str {
    let s = &*t;

    s.split_at(s.rfind('-').unwrap_or(0)).0
}
