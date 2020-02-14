// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::stream::TryStreamExt;
use iml_manager_env::{get_influxdb_addr, get_influxdb_metrics_db};
use iml_service_queue::service_queue::consume_data;
use iml_stats::error::ImlStatsError;
use influxdb::{Client, Query, Timestamp};
use lustre_collector::{HostStats, LNetStats, Record, TargetStats};
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

        let client = Client::new(&influx_url, get_influxdb_metrics_db());
        //Write the entry into the influxdb database
        for record in xs {
            let maybe_entries = match record {
                Record::Target(target_stats) => match target_stats {
                    TargetStats::Stats(x) => Some(
                        x.value
                            .iter()
                            .map(|stat| {
                                Query::write_query(Timestamp::Now, "target")
                                    .add_tag("host", host.0.as_ref())
                                    .add_tag("target", &*x.target)
                                    .add_tag("name", &*stat.name)
                                    .add_tag("units", &*stat.units)
                                    .add_field("min", stat.min)
                                    .add_field("max", stat.max)
                                    .add_field("sum", stat.sum)
                                    .add_field("sumsquare", stat.sumsquare)
                            })
                            .collect(),
                    ),
                    TargetStats::BrwStats(x) => Some(
                        x.value
                            .iter()
                            .flat_map(|brw_stat| {
                                brw_stat
                                    .buckets
                                    .iter()
                                    .map(|bucket| {
                                        Query::write_query(Timestamp::Now, "target")
                                            .add_tag("host", host.0.as_ref())
                                            .add_tag("target", &*x.target)
                                            .add_tag("name", &*brw_stat.name)
                                            .add_tag("unit", &*brw_stat.unit)
                                            .add_tag("bucket_name", bucket.name)
                                            .add_field("read", bucket.read)
                                            .add_field("write", bucket.write)
                                    })
                                    .collect::<Vec<_>>()
                            })
                            .collect(),
                    ),
                    TargetStats::FilesFree(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("bytes_free", x.value)])
                    }
                    TargetStats::FilesTotal(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("files_total", x.value)])
                    }
                    TargetStats::FsType(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("fs_type", x.value)])
                    }
                    TargetStats::BytesAvail(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("bytes_avail", x.value)])
                    }
                    TargetStats::BytesFree(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("bytes_free", x.value)])
                    }
                    TargetStats::BytesTotal(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("bytes_total", x.value)])
                    }
                    TargetStats::NumExports(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("num_exports", x.value)])
                    }
                    TargetStats::TotDirty(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("tot_dirty", x.value)])
                    }
                    TargetStats::TotGranted(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("tot_granted", x.value)])
                    }
                    TargetStats::TotPending(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("tot_pending", x.value)])
                    }
                    TargetStats::ContendedLocks(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("contended_locks", x.value)])
                    }
                    TargetStats::ContentionSeconds(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("contention_seconds", x.value)])
                    }
                    TargetStats::CtimeAgeLimit(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("ctime_age_limit", x.value)])
                    }
                    TargetStats::EarlyLockCancel(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("early_lock_cancel", x.value)])
                    }
                    TargetStats::LockCount(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("lock_count", x.value)])
                    }
                    TargetStats::LockTimeouts(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("lock_timeouts", x.value)])
                    }
                    TargetStats::LockUnusedCount(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("lock_unused_count", x.value)])
                    }
                    TargetStats::LruMaxAge(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("lru_max_age", x.value)])
                    }
                    TargetStats::LruSize(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("lru_size", x.value)])
                    }
                    TargetStats::MaxNolockBytes(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("max_no_lock_bytes", x.value)])
                    }
                    TargetStats::MaxParallelAst(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("max_parallel_ast", x.value)])
                    }
                    TargetStats::ResourceCount(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("resource_count", x.value)])
                    }
                    TargetStats::ThreadsMin(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("threads_min", x.value)])
                    }
                    TargetStats::ThreadsMax(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("threads_max", x.value)])
                    }
                    TargetStats::ThreadsStarted(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "target")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("target", &*x.target)
                            .add_field("threads_started", x.value)])
                    }
                    _ => {
                        tracing::debug!("Received target stat type that is not implemented yet.");

                        None
                    }
                },
                Record::Host(host_stats) => match host_stats {
                    HostStats::MemusedMax(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "host")
                            .add_tag("host", host.0.as_ref())
                            .add_field("memused_max", x.value)])
                    }
                    HostStats::Memused(x) => Some(vec![Query::write_query(Timestamp::Now, "host")
                        .add_tag("host", host.0.as_ref())
                        .add_field("memused", x.value)]),
                    HostStats::LNetMemUsed(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "host")
                            .add_tag("host", host.0.as_ref())
                            .add_field("lnet_mem_used", x.value)])
                    }
                    HostStats::HealthCheck(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "host")
                            .add_tag("host", host.0.as_ref())
                            .add_field("health_check", x.value)])
                    }
                },
                Record::LNetStat(lnet_stats) => match lnet_stats {
                    LNetStats::SendCount(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "host")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("nid", x.nid)
                            .add_field("send_count", x.value)])
                    }
                    LNetStats::RecvCount(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "host")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("nid", x.nid)
                            .add_field("recv_count", x.value)])
                    }
                    LNetStats::DropCount(x) => {
                        Some(vec![Query::write_query(Timestamp::Now, "host")
                            .add_tag("host", host.0.as_ref())
                            .add_tag("nid", x.nid)
                            .add_field("drop_count", x.value)])
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
