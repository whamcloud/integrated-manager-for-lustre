use crate::{Error, MonitorState};
use emf_command_utils::wait_for_cmds_success;
use emf_graphql_queries::snapshot as snapshot_queries;
use emf_manager_client::{get_influx, graphql, Client};
use emf_postgres::{sqlx, PgPool};
use emf_tracing::tracing;
use std::{collections::HashMap, fmt::Debug};
use tokio::time::{Duration, Instant};

pub async fn tick(
    snapshot_client_counts: &mut HashMap<i32, MonitorState>,
    pool: PgPool,
) -> Result<(), Error> {
    let client: Client = emf_manager_client::get_client()?;
    let client_2 = client.clone();

    let query = emf_influx::filesystems::query();
    let stats_fut =
        get_influx::<emf_influx::filesystems::InfluxResponse>(client, "emf_stats", query.as_str());

    let influx_resp = stats_fut.await?;
    let stats = emf_influx::filesystems::Response::from(influx_resp);

    tracing::debug!("Influx stats: {:?}", stats);

    let snapshots =
        sqlx::query!("SELECT id, filesystem_name, snapshot_name, snapshot_fsname FROM snapshot")
            .fetch_all(&pool)
            .await?;
    tracing::debug!("Fetched {} snapshots from DB", snapshots.len());

    for snapshot in snapshots {
        let snapshot_id = snapshot.id;
        let snapshot_stats = match stats.get(&snapshot.snapshot_fsname) {
            Some(x) => x,
            None => continue,
        };

        let monitor_state = snapshot_client_counts.get_mut(&snapshot_id);
        let clients = snapshot_stats.clients.unwrap_or(0);

        match monitor_state {
            Some(MonitorState::Monitoring(prev_clients)) => {
                tracing::debug!(
                    "Monitoring. Snapshot {}: {} clients (previously {} clients)",
                    &snapshot.snapshot_fsname,
                    clients,
                    prev_clients,
                );
                if *prev_clients > 0 && clients == 0 {
                    tracing::trace!("counting down for job");
                    let instant = Instant::now() + Duration::from_secs(5 * 60);
                    monitor_state.map(|s| *s = MonitorState::CountingDown(instant));
                } else {
                    *prev_clients = clients;
                }
            }
            Some(MonitorState::CountingDown(when)) => {
                tracing::debug!(
                    "Counting down. Snapshot {}: 0 clients (previously {} clients)",
                    &snapshot.snapshot_fsname,
                    clients
                );
                if clients > 0 {
                    tracing::trace!("changing MonitorState");
                    monitor_state.map(|s| *s = MonitorState::Monitoring(clients));
                } else if Instant::now() >= *when {
                    tracing::trace!("running the job");
                    monitor_state.map(|s| *s = MonitorState::Monitoring(0));

                    let query = snapshot_queries::unmount::build(
                        &snapshot.filesystem_name,
                        &snapshot.snapshot_name,
                    );
                    let resp: emf_graphql_queries::Response<snapshot_queries::unmount::Resp> =
                        graphql(client_2.clone(), query).await?;
                    let command = Result::from(resp)?.data.unmount_snapshot;
                    wait_for_cmds_success(&[command], None).await?;
                }
            }
            None => {
                tracing::debug!(
                    "Just learnt about this snapshot. Snapshot {}: {} clients",
                    &snapshot.snapshot_fsname,
                    clients,
                );

                snapshot_client_counts.insert(snapshot_id, MonitorState::Monitoring(clients));
            }
        }
    }

    Ok(())
}
