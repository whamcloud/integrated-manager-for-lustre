// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::stream::TryStreamExt;
use iml_manager_env::{get_influxdb_addr, get_influxdb_metrics_db};
use iml_service_queue::service_queue::consume_data;
use iml_stats::error::ImlStatsError;
use influxdb::{Client, Query, Timestamp};
use lustre_collector::{HostStats, LNetStats, NodeStats, Record, TargetStats};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};

#[tokio::main]
async fn main() -> Result<(), ImlStatsError> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let mut s = consume_data::<Vec<Record>>("rust_agent_stats_rx");
    let influx_url: String = format!("http://{}", get_influxdb_addr());
    tracing::debug!("influx_url: {}", &influx_url);

    while let Some((host, xs)) = s.try_next().await? {
        tracing::info!("Incoming stats: {}: {:?}", host, xs);
        tracing::info!("host: {:?}", host.0);
        let client = Client::new(&influx_url, get_influxdb_metrics_db());
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::SystemTime::UNIX_EPOCH)?
            .as_nanos() as usize;
        tracing::info!("ts: {}", ts);

        //Write the entry into the influxdb database
        for record in xs {
            let maybe_entries = match record {
                Record::Target(target_stats) => match target_stats {
                    TargetStats::Stats(x) => {
                        tracing::debug!("Stats: {:?}", x);
                        Some(
                            x.value
                                .iter()
                                .map(|stat| {
                                    let mut query =
                                        Query::write_query(Timestamp::Nanoseconds(ts), "target")
                                            .add_tag("host", host.0.as_ref())
                                            .add_tag("target", &*x.target)
                                            .add_tag("kind", x.kind.to_string())
                                            .add_tag("name", &*stat.name)
                                            .add_tag("units", &*stat.units)
                                            .add_field("samples", stat.samples);

                                    if let Some(min) = stat.min {
                                        query = query.add_field("min", min);
                                        tracing::debug!("Target Stat - min: {}", min);
                                    }

                                    if let Some(max) = stat.max {
                                        query = query.add_field("max", max);
                                        tracing::debug!("Target Stat - max: {}", max);
                                    }

                                    if let Some(sum) = stat.sum {
                                        query = query.add_field("sum", sum);
                                        tracing::debug!("Target Stat - sum: {}", sum);
                                    }

                                    if let Some(sumsquare) = stat.sumsquare {
                                        query = query.add_field("sumsquare", sumsquare);
                                        tracing::debug!("Target Stat - sumsquare: {}", sumsquare);
                                    }
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
                    TargetStats::BrwStats(x) => {
                        tracing::debug!("BrwStats: {:?}", x);
                        Some(
                        x.value
                            .iter()
                            .flat_map(|brw_stat| {
                                brw_stat
                                    .buckets
                                    .iter()
                                    .map(|bucket| {
                                        let query = Query::write_query(
                                            Timestamp::Nanoseconds(ts),
                                            "target",
                                        )
                                        .add_tag("host", host.0.as_ref())
                                        .add_tag("target", &*x.target)
                                        .add_tag("kind", x.kind.to_string())
                                        .add_tag("name", &*brw_stat.name)
                                        .add_tag("unit", &*brw_stat.unit)
                                        .add_tag("bucket_name", bucket.name)
                                        .add_field("read", bucket.read)
                                        .add_field("write", bucket.write);

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
                    TargetStats::FilesFree(x) => {
                        tracing::debug!("FilesFree - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("target", &*x.target)
                        .add_tag("kind", x.kind.to_string())
                        .add_field("files_free", x.value)])
                    }
                    TargetStats::FilesTotal(x) => {
                        tracing::debug!("FilesTotal - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("files_total", x.value)])
                    }
                    TargetStats::FsType(x) => {
                        tracing::debug!("FsType - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("fs_type", x.value)])
                    }
                    TargetStats::BytesAvail(x) => {
                        tracing::debug!("BytesAvail - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("bytes_avail", x.value)])
                    }
                    TargetStats::BytesFree(x) => {
                        tracing::debug!("BytesFree - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("bytes_free", x.value)])
                    }
                    TargetStats::BytesTotal(x) => {
                        tracing::debug!("BytesTotal - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("bytes_total", x.value)])
                    }
                    TargetStats::NumExports(x) => {
                        tracing::debug!("NumExports - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("num_exports", x.value)])
                    }
                    TargetStats::TotDirty(x) => {
                        tracing::debug!("TotDirty - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("tot_dirty", x.value)])
                    }
                    TargetStats::TotGranted(x) => {
                        tracing::debug!("TotGranted - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("tot_granted", x.value)])
                    }
                    TargetStats::TotPending(x) => {
                        tracing::debug!("TotPending - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("tot_pending", x.value)])
                    }
                    TargetStats::ContendedLocks(x) => {
                        tracing::debug!("ContendedLocks - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("contended_locks", x.value)])
                    }
                    TargetStats::ContentionSeconds(x) => {
                        tracing::debug!("ContentionSeconds - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("contention_seconds", x.value)])
                    }
                    TargetStats::CtimeAgeLimit(x) => {
                        tracing::debug!("CtimeAgeLimit - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("ctime_age_limit", x.value)])
                    }
                    TargetStats::EarlyLockCancel(x) => {
                        tracing::debug!("EarlyLockCancel - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("early_lock_cancel", x.value)])
                    }
                    TargetStats::LockCount(x) => {
                        tracing::debug!("TargetStats - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("lock_count", x.value)])
                    }
                    TargetStats::LockTimeouts(x) => {
                        tracing::debug!("LockTimeouts - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("lock_timeouts", x.value)])
                    }
                    TargetStats::LockUnusedCount(x) => {
                        tracing::debug!("LockUnusedCount - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("lock_unused_count", x.value)])
                    }
                    TargetStats::LruMaxAge(x) => {
                        tracing::debug!("LruMaxAge - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("lru_max_age", x.value)])
                    }
                    TargetStats::LruSize(x) => {
                        tracing::debug!("LruSize - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("lru_size", x.value)])
                    }
                    TargetStats::MaxNolockBytes(x) => {
                        tracing::debug!("MaxNolockBytes - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("max_no_lock_bytes", x.value)])
                    }
                    TargetStats::MaxParallelAst(x) => {
                        tracing::debug!("MaxParallelAst - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("max_parallel_ast", x.value)])
                    }
                    TargetStats::ResourceCount(x) => {
                        tracing::debug!("ResourceCount - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("resource_count", x.value)])
                    }
                    TargetStats::ThreadsMin(x) => {
                        tracing::debug!("ThreadsMin - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("threads_min", x.value)])
                    }
                    TargetStats::ThreadsMax(x) => {
                        tracing::debug!("ThreadsMax - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("threads_max", x.value)])
                    }
                    TargetStats::ThreadsStarted(x) => {
                        tracing::debug!("ThreadsStarted - {:?}", x);
                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("threads_started", x.value)])
                    }
                    TargetStats::ConnectedClients(x) => {
                        tracing::debug!("ConnectedClients - {:?}", x);

                        Some(vec![Query::write_query(
                            Timestamp::Nanoseconds(ts),
                            "target",
                        )
                        .add_tag("host", host.0.as_ref())
                        .add_tag("kind", x.kind.to_string())
                        .add_tag("target", &*x.target)
                        .add_field("connected_clients", x.value)])
                    }
                    TargetStats::JobStatsOst(_) => {
                        // Not storing jobstats... yet.
                        None
                    }
                },
                Record::Host(host_stats) => match host_stats {
                    HostStats::MemusedMax(x) => {
                        tracing::debug!("MemusedMax - {:?}", x);
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "host")
                            .add_tag("host", host.0.as_ref())
                            .add_field("memused_max", x.value)])
                    }
                    HostStats::Memused(x) => {
                        tracing::debug!("Memused - {:?}", x);
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "host")
                            .add_tag("host", host.0.as_ref())
                            .add_field("memused", x.value)])
                    }
                    HostStats::LNetMemUsed(x) => {
                        tracing::debug!("LNetMemUsed - {:?}", x);
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "host")
                            .add_tag("host", host.0.as_ref())
                            .add_field("lnet_mem_used", x.value)])
                    }
                    HostStats::HealthCheck(x) => {
                        tracing::debug!("HealthCheck - {:?}", x);
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "host")
                            .add_tag("host", host.0.as_ref())
                            .add_field("health_check", x.value)])
                    }
                },
                Record::LNetStat(lnet_stats) => match lnet_stats {
                    LNetStats::SendCount(x) => {
                        tracing::debug!("SendCount - {:?}", x);
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "lnet")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("nid", x.nid)
                            .add_field("send_count", x.value)])
                    }
                    LNetStats::RecvCount(x) => {
                        tracing::debug!("RecvCount - {:?}", x);
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "lnet")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("nid", x.nid)
                            .add_field("recv_count", x.value)])
                    }
                    LNetStats::DropCount(x) => {
                        tracing::debug!("DropCount - {:?}", x);
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "lnet")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("nid", x.nid)
                            .add_field("drop_count", x.value)])
                    }
                },
                Record::Node(node) => match node {
                    NodeStats::CpuUser(x) => {
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "node")
                            .add_tag("host", host.0.as_ref())
                            .add_field("cpu_user", x.value)])
                    }
                    NodeStats::CpuSystem(x) => {
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "node")
                            .add_tag("host", host.0.as_ref())
                            .add_field("cpu_system", x.value)])
                    }
                    NodeStats::CpuIowait(x) => {
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "node")
                            .add_tag("host", host.0.as_ref())
                            .add_field("cpu_iowait", x.value)])
                    }
                    NodeStats::CpuTotal(x) => {
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "node")
                            .add_tag("host", host.0.as_ref())
                            .add_field("cpu_total", x.value)])
                    }
                    NodeStats::MemTotal(x) => {
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "node")
                            .add_tag("host", host.0.as_ref())
                            .add_field("mem_total", x.value)])
                    }
                    NodeStats::MemFree(x) => {
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "node")
                            .add_tag("host", host.0.as_ref())
                            .add_field("mem_free", x.value)])
                    }
                    NodeStats::SwapTotal(x) => {
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "node")
                            .add_tag("host", host.0.as_ref())
                            .add_field("swap_total", x.value)])
                    }
                    NodeStats::SwapFree(x) => {
                        Some(vec![Query::write_query(Timestamp::Nanoseconds(ts), "node")
                            .add_tag("host", host.0.as_ref())
                            .add_field("swap_free", x.value)])
                    }
                },
            };

            if let Some(entries) = maybe_entries {
                for entry in entries {
                    let r = client.query(&entry).await?;

                    tracing::debug!("Result of writing series to influxdb: {}", r);
                }
            }
        }
    }

    Ok(())
}
