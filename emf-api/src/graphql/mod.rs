// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod filesystem;
mod host;
mod ostpool;
mod stratagem;
mod task;

use crate::{
    error::EmfApiError,
    timer::{configure_snapshot_timer, remove_snapshot_timer},
};
use chrono::{DateTime, Utc};
use emf_postgres::{active_mgs_host_fqdn, fqdn_by_host_id, get_fs_target_resources};
use emf_wire_types::{
    db::{LogMessageRecord, LustreFid},
    graphql_duration::GraphQLDuration,
    logs::{LogResponse, Meta},
    snapshot::{ReserveUnit, Snapshot, SnapshotInterval, SnapshotRetention},
    task::Task,
    BannedResource, Command, FsType, LogMessage, LogSeverity, MessageClass, SortDir, TargetRecord,
    TargetResource,
};
use futures::{future::join_all, TryStreamExt};
use itertools::Itertools;
use juniper::{
    http::{graphiql::graphiql_source, GraphQLRequest},
    EmptySubscription, FieldError, RootNode, Value,
};
use sqlx::{
    self,
    postgres::{types::PgInterval, PgPool},
};
use std::{
    collections::{HashMap, HashSet},
    convert::{Infallible, TryFrom as _, TryInto},
    ops::Deref,
    str::FromStr,
    sync::Arc,
};
use warp::Filter;

#[derive(juniper::GraphQLObject)]
/// A Corosync Node found in `crm_mon`
struct CorosyncNode {
    /// The name of the node
    name: String,
    /// The id of the node as reported by `crm_mon`
    id: String,
    /// Id of the cluster this node belongs to
    cluster_id: i32,
    online: bool,
    standby: bool,
    standby_onfail: bool,
    maintenance: bool,
    pending: bool,
    unclean: bool,
    shutdown: bool,
    expected_up: bool,
    is_dc: bool,
    resources_running: i32,
    r#type: String,
}

#[derive(Debug, serde::Serialize)]
pub struct SendJob<'a, T> {
    pub class_name: &'a str,
    pub args: T,
}

pub(crate) struct QueryRoot;

#[juniper::graphql_object(Context = Context)]
impl QueryRoot {
    fn host(&self) -> host::HostQuery {
        host::HostQuery
    }
    fn filesystem(&self) -> filesystem::FilesystemQuery {
        filesystem::FilesystemQuery
    }
    fn ost_pool(&self) -> ostpool::OstPoolQuery {
        ostpool::OstPoolQuery
    }
    fn stratagem(&self) -> stratagem::StratagemQuery {
        stratagem::StratagemQuery
    }
    fn task(&self) -> task::TaskQuery {
        task::TaskQuery
    }
    /// Given a host id, try to find the matching corosync node name
    #[graphql(arguments(host_id(description = "The id to search on")))]
    async fn corosync_node_name_by_host(
        context: &Context,
        host_id: i32,
    ) -> juniper::FieldResult<Option<String>> {
        let x = sqlx::query!(
            r#"
                SELECT (nmh.corosync_node_id).name AS "name!" FROM corosync_node_host nmh
                WHERE host_id = $1
            "#,
            host_id
        )
        .fetch_optional(&context.pg_pool)
        .await?
        .map(|x| x.name);

        Ok(x)
    }
    #[graphql(arguments(
        limit(description = "optional paging limit, defaults to all rows"),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to asc")
    ))]
    async fn corosync_nodes(
        context: &Context,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
    ) -> juniper::FieldResult<Vec<CorosyncNode>> {
        let dir = dir.unwrap_or_default();

        let xs = sqlx::query_as!(
            CorosyncNode,
            r#"
                SELECT
                (n.id).name AS "name!",
                (n.id).id AS "id!",
                cluster_id,
                online,
                standby,
                standby_onfail,
                maintenance,
                pending,
                unclean,
                shutdown,
                expected_up,
                is_dc,
                resources_running,
                type
                FROM corosync_node n
                ORDER BY
                    CASE WHEN $1 = 'ASC' THEN n.id END ASC,
                    CASE WHEN $1 = 'DESC' THEN n.id END DESC
                OFFSET $2 LIMIT $3"#,
            dir.deref(),
            offset.unwrap_or(0) as i64,
            limit.map(|x| x as i64),
        )
        .fetch_all(&context.pg_pool)
        .await?;

        Ok(xs)
    }

    #[graphql(arguments(
        limit(description = "optional paging limit, defaults to all rows"),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to asc"),
        fs_name(description = "Targets associated with the specified filesystem"),
        exclude_unmounted(description = "Exclude unmounted targets, defaults to false"),
    ))]
    /// Fetch the list of known targets
    async fn targets(
        context: &Context,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
        fs_name: Option<String>,
        exclude_unmounted: Option<bool>,
    ) -> juniper::FieldResult<Vec<TargetRecord>> {
        let dir = dir.unwrap_or_default();

        if let Some(ref fs_name) = fs_name {
            let _ = fs_id_by_name(&context.pg_pool, &fs_name).await?;
        }

        let xs: Vec<TargetRecord> = sqlx::query_as!(
            TargetRecord,
            r#"
                SELECT id, state, name, active_host_id, host_ids, filesystems, uuid, mount_path, dev_path, fs_type as "fs_type: FsType" from target t
                ORDER BY
                    CASE WHEN $3 = 'ASC' THEN t.name END ASC,
                    CASE WHEN $3 = 'DESC' THEN t.name END DESC
                OFFSET $1 LIMIT $2"#,
            offset.unwrap_or(0) as i64,
            limit.map(|x| x as i64),
            dir.deref()
        )
        .fetch_all(&context.pg_pool)
        .await?
        .into_iter()
        .filter(|x| match &fs_name {
            Some(fs) => x.filesystems.contains(&fs),
            None => true,
        })
        .filter(|x| match exclude_unmounted {
            Some(true) => x.state != "unmounted",
            Some(false) | None => true,
        })
        .collect();

        let target_resources = get_fs_target_resources(&context.pg_pool, None).await?;

        let xs: Vec<TargetRecord> = xs
            .into_iter()
            .map(|mut x| {
                let resource = target_resources
                    .iter()
                    .find(|resource| resource.name == x.name);

                if let Some(resource) = resource {
                    x.host_ids = resource.cluster_hosts.clone();
                }

                x
            })
            .collect();

        Ok(xs)
    }

    /// Given a `fs_name`, produce a list of `TargetResource`.
    /// Each `TargetResource` will list the host ids it's capable of
    /// running on, taking bans into account.
    #[graphql(arguments(fs_name(description = "The filesystem to list `TargetResource`s for"),))]
    async fn get_fs_target_resources(
        context: &Context,
        fs_name: Option<String>,
    ) -> juniper::FieldResult<Vec<TargetResource>> {
        if let Some(ref fs_name) = fs_name {
            let _ = fs_id_by_name(&context.pg_pool, &fs_name).await?;
        }
        let xs = get_fs_target_resources(&context.pg_pool, fs_name).await?;

        Ok(xs)
    }

    async fn get_banned_resources(context: &Context) -> juniper::FieldResult<Vec<BannedResource>> {
        let xs = get_banned_resources(&context.pg_pool).await?;

        Ok(xs)
    }

    /// Given a `fs_name`, produce a distinct grouping
    /// of cluster nodes that make up the filesystem.
    /// This is useful to find nodes capable of running resources associated
    /// with the given `fs_name`.
    #[graphql(arguments(fs_name(description = "The filesystem to search cluster nodes for")))]
    async fn get_fs_cluster_hosts(
        context: &Context,
        fs_name: String,
    ) -> juniper::FieldResult<Vec<Vec<String>>> {
        let _ = fs_id_by_name(&context.pg_pool, &fs_name).await?;
        let xs = get_fs_cluster_hosts(&context.pg_pool, fs_name).await?;

        Ok(xs)
    }

    #[graphql(arguments(
        limit(description = "optional paging limit, defaults to all rows"),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to ASC"),
        fsname(description = "Filesystem the snapshot was taken from"),
        name(description = "Name of the snapshot"),
    ))]
    /// Fetch the list of snapshots
    async fn snapshots(
        context: &Context,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
        fsname: String,
        name: Option<String>,
    ) -> juniper::FieldResult<Vec<Snapshot>> {
        let dir = dir.unwrap_or_default();

        let _ = fs_id_by_name(&context.pg_pool, &fsname).await?;

        let snapshots = sqlx::query_as!(
            Snapshot,
                r#"
                    SELECT filesystem_name, snapshot_name, create_time, modify_time, snapshot_fsname, mounted, comment FROM snapshot s
                    WHERE filesystem_name = $4 AND ($5::text IS NULL OR snapshot_name = $5)
                    ORDER BY
                        CASE WHEN $3 = 'ASC' THEN s.create_time END ASC,
                        CASE WHEN $3 = 'DESC' THEN s.create_time END DESC
                    OFFSET $1 LIMIT $2"#,
                offset.unwrap_or(0) as i64,
                limit.map(|x| x as i64),
                dir.deref(),
                fsname,
                name,
            )
            .fetch_all(&context.pg_pool)
            .await?;

        Ok(snapshots)
    }

    /// Fetch the list of commands
    #[graphql(arguments(
        limit(description = "optional paging limit, defaults to all rows"),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to ASC"),
        is_active(description = "Command status, active means not completed, default is true"),
        msg(description = "Substring of the command's message, null or empty matches all"),
    ))]

    /// List all snapshot intervals
    async fn snapshot_intervals(context: &Context) -> juniper::FieldResult<Vec<SnapshotInterval>> {
        let xs: Vec<SnapshotInterval> = sqlx::query!("SELECT * FROM snapshot_interval")
            .fetch(&context.pg_pool)
            .map_ok(|x| SnapshotInterval {
                id: x.id,
                filesystem_name: x.filesystem_name,
                use_barrier: x.use_barrier,
                interval: x.interval.into(),
                last_run: x.last_run,
            })
            .try_collect()
            .await?;

        Ok(xs)
    }
    /// List all snapshot retention policies. Snapshots will automatically be deleted (starting with the oldest)
    /// when free space falls below the defined reserve value and its associated unit.
    async fn snapshot_retention_policies(
        context: &Context,
    ) -> juniper::FieldResult<Vec<SnapshotRetention>> {
        let xs: Vec<SnapshotRetention> = sqlx::query_as!(
            SnapshotRetention,
            r#"
                SELECT
                    id,
                    filesystem_name,
                    reserve_value,
                    reserve_unit as "reserve_unit:ReserveUnit",
                    last_run,
                    keep_num
                FROM snapshot_retention
            "#
        )
        .fetch(&context.pg_pool)
        .try_collect()
        .await?;

        Ok(xs)
    }

    #[graphql(arguments(
        limit(description = "optional paging limit, defaults to 100",),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to asc"),
        message(
            description = "Pattern to search for in message. Uses Postgres pattern matching  (https://www.postgresql.org/docs/9.6/functions-matching.html)"
        ),
        fqdn(
            description = "Pattern to search for in FQDN. Uses Postgres pattern matching  (https://www.postgresql.org/docs/9.6/functions-matching.html)"
        ),
        tag(
            description = "Pattern to search for in tag. Uses Postgres pattern matching  (https://www.postgresql.org/docs/9.6/functions-matching.html)"
        ),
        start_datetime(description = "Start of the time period of logs"),
        end_datetime(description = "End of the time period of logs"),
        message_class(description = "Array of log message classes"),
        severity(description = "Upper bound of log severity"),
    ))]
    /// Returns aggregated journal entries for all nodes the agent runs on.
    async fn logs(
        context: &Context,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
        message: Option<String>,
        fqdn: Option<String>,
        tag: Option<String>,
        start_datetime: Option<chrono::DateTime<Utc>>,
        end_datetime: Option<chrono::DateTime<Utc>>,
        message_class: Option<Vec<MessageClass>>,
        severity: Option<LogSeverity>,
    ) -> juniper::FieldResult<LogResponse> {
        let dir = dir.unwrap_or_default();

        let message_class: Vec<_> = message_class
            .filter(|v| !v.is_empty())
            .unwrap_or_else(|| vec![MessageClass::Normal])
            .into_iter()
            .map(|i| i as i16)
            .collect();

        let severity = severity.unwrap_or(LogSeverity::Informational) as i16;

        let results = sqlx::query_as!(
            LogMessageRecord,
            r#"
                    SELECT * FROM logmessage t
                    WHERE ($4::TEXT IS NULL OR t.message LIKE $4)
                      AND ($5::TEXT IS NULL OR t.fqdn LIKE $5)
                      AND ($6::TEXT IS NULL OR t.tag LIKE $6)
                      AND ($7::TIMESTAMPTZ IS NULL OR t.datetime >= $7)
                      AND ($8::TIMESTAMPTZ IS NULL OR t.datetime < $8)
                      AND ARRAY[t.message_class] <@ $9
                      AND t.severity <= $10
                    ORDER BY
                        CASE WHEN $3 = 'ASC' THEN t.datetime END ASC,
                        CASE WHEN $3 = 'DESC' THEN t.datetime END DESC
                    OFFSET $1 LIMIT $2"#,
            offset.unwrap_or(0) as i64,
            limit.map(|x| x as i64).unwrap_or(100),
            dir.deref(),
            message,
            fqdn,
            tag,
            start_datetime,
            end_datetime,
            &message_class,
            severity,
        )
        .fetch_all(&context.pg_pool)
        .await?;
        let xs: Vec<LogMessage> = results
            .into_iter()
            .map(|x| x.try_into())
            .collect::<Result<_, _>>()?;

        let total_count =
            sqlx::query!("SELECT total_rows FROM rowcount WHERE table_name = 'logmessage'")
                .fetch_one(&context.pg_pool)
                .await?
                .total_rows
                .ok_or_else(|| {
                    FieldError::new("Number of rows doesn't fit in i32", Value::null())
                })?;

        Ok(LogResponse {
            data: xs,
            meta: Meta {
                total_count: total_count.try_into()?,
            },
        })
    }

    /// List the client mount source.
    /// This will build up the source using known mgs locations
    /// for the given filesystem.
    #[graphql(arguments(fs(description = "The filesystem to generate the source for"),))]
    async fn client_mount_source(
        context: &Context,
        fs_name: String,
    ) -> juniper::FieldResult<String> {
        let x = client_mount_source(&context.pg_pool, &fs_name).await?;

        Ok(x)
    }
    /// List the full client mount command.
    /// This will build up the source using known mgs locations
    /// for the given filesystem.
    /// The output can be directly pasted on a server to mount a client,
    /// after the mount directory has been created.
    #[graphql(arguments(fs(description = "The filesystem to generate the mount command for"),))]
    async fn client_mount_command(
        context: &Context,
        fs_name: String,
    ) -> juniper::FieldResult<String> {
        let x = client_mount_source(&context.pg_pool, &fs_name).await?;

        let mount_command = format!("mount -t lustre {} /mnt/{}", x, fs_name);

        Ok(mount_command)
    }
}

struct SnapshotIntervalName {
    id: i32,
    fs_name: String,
    timestamp: DateTime<Utc>,
}

fn parse_snapshot_name(name: &str) -> Option<SnapshotIntervalName> {
    match name.trim().splitn(3, '-').collect::<Vec<&str>>().as_slice() {
        [id, fs, ts] => {
            let ts = ts.parse::<DateTime<Utc>>().ok()?;
            let id = id.parse::<i32>().ok()?;

            Some(SnapshotIntervalName {
                id,
                fs_name: fs.to_string(),
                timestamp: ts,
            })
        }
        _ => None,
    }
}

pub(crate) struct MutationRoot;

#[juniper::graphql_object(Context = Context)]
impl MutationRoot {
    fn stratagem(&self) -> stratagem::StratagemMutation {
        stratagem::StratagemMutation
    }
    fn task(&self) -> task::TaskMutation {
        task::TaskMutation
    }
    #[graphql(arguments(
        fsname(description = "Filesystem to snapshot"),
        name(description = "Name of the snapshot"),
        comment(description = "A description for the purpose of the snapshot"),
        use_barrier(
            description = "Set write barrier before creating snapshot. The default value is `false`"
        )
    ))]
    /// Creates a snapshot of an existing Lustre filesystem. Returns a `Command` to track progress.
    /// For the `Command` to succeed, the filesystem being snapshoted must be available.
    async fn create_snapshot(
        context: &Context,
        fsname: String,
        name: String,
        comment: Option<String>,
        use_barrier: Option<bool>,
    ) -> juniper::FieldResult<Command> {
        let _ = fs_id_by_name(&context.pg_pool, &fsname).await?;
        let name = name.trim();
        validate_snapshot_name(name)?;

        let snapshot_interval_name = parse_snapshot_name(name);
        if let Some(data) = snapshot_interval_name {
            sqlx::query!(
                r#"
                UPDATE snapshot_interval
                SET last_run=$1
                WHERE id=$2 AND filesystem_name=$3
            "#,
                data.timestamp,
                data.id,
                data.fs_name,
            )
            .execute(&context.pg_pool)
            .await?;
        }

        let active_mgs_host_fqdn = active_mgs_host_fqdn(&fsname, &context.pg_pool)
            .await?
            .ok_or_else(|| {
                FieldError::new("Filesystem not found or MGS is not mounted", Value::null())
            })?;

        let kwargs: HashMap<String, String> = vec![("message".into(), "Creating snapshot".into())]
            .into_iter()
            .collect();

        let jobs = serde_json::json!([{
            "class_name": "CreateSnapshotJob",
            "args": {
                "fsname": fsname,
                "name": name,
                "comment": comment,
                "fqdn": active_mgs_host_fqdn,
                "use_barrier": use_barrier.unwrap_or(false),
            }
        }]);

        todo!();
    }
    #[graphql(arguments(
        fsname(description = "Filesystem snapshot was taken from"),
        name(description = "Name of the snapshot"),
        force(description = "Destroy the snapshot by force"),
    ))]
    /// Destroys an existing snapshot of an existing Lustre filesystem. Returns a `Command` to track progress.
    /// For the `Command` to succeed, the filesystem must be available.
    async fn destroy_snapshot(
        context: &Context,
        fsname: String,
        name: String,
        force: bool,
    ) -> juniper::FieldResult<Command> {
        let _ = fs_id_by_name(&context.pg_pool, &fsname).await?;
        let name = name.trim();
        validate_snapshot_name(name)?;

        let active_mgs_host_fqdn = active_mgs_host_fqdn(&fsname, &context.pg_pool)
            .await?
            .ok_or_else(|| {
                FieldError::new("Filesystem not found or MGS is not mounted", Value::null())
            })?;

        let kwargs: HashMap<String, String> =
            vec![("message".into(), "Destroying snapshot".into())]
                .into_iter()
                .collect();

        let jobs = serde_json::json!([{
            "class_name": "DestroySnapshotJob",
            "args": {
                "fsname": fsname,
                "name": name,
                "force": force,
                "fqdn": active_mgs_host_fqdn,
            }
        }]);

        todo!();
    }
    #[graphql(arguments(
        fsname(description = "Filesystem snapshot was taken from"),
        name(description = "Name of the snapshot"),
    ))]
    /// Mounts an existing snapshot of an existing Lustre filesystem. Returns a `Command` to track progress.
    /// For the `Command` to succeed, the filesystem must be available.
    async fn mount_snapshot(
        context: &Context,
        fsname: String,
        name: String,
    ) -> juniper::FieldResult<Command> {
        let name = name.trim();
        validate_snapshot_name(name)?;

        let active_mgs_host_fqdn = active_mgs_host_fqdn(&fsname, &context.pg_pool)
            .await?
            .ok_or_else(|| {
                FieldError::new("Filesystem not found or MGS is not mounted", Value::null())
            })?;

        let kwargs: HashMap<String, String> = vec![("message".into(), "Mounting snapshot".into())]
            .into_iter()
            .collect();

        let jobs = serde_json::json!([{
            "class_name": "MountSnapshotJob",
            "args": {
                "fsname": fsname,
                "name": name,
                "fqdn": active_mgs_host_fqdn,
            }
        }]);

        todo!();
    }
    #[graphql(arguments(
        fsname(description = "Filesystem snapshot was taken from"),
        name(description = "Name of the snapshot"),
    ))]
    /// Unmounts an existing snapshot of an existing Lustre filesystem. Returns a `Command` to track progress.
    /// For the `Command` to succeed, the filesystem must be available.
    async fn unmount_snapshot(
        context: &Context,
        fsname: String,
        name: String,
    ) -> juniper::FieldResult<Command> {
        let _ = fs_id_by_name(&context.pg_pool, &fsname).await?;
        let name = name.trim();
        validate_snapshot_name(name)?;

        let active_mgs_host_fqdn = active_mgs_host_fqdn(&fsname, &context.pg_pool)
            .await?
            .ok_or_else(|| {
                FieldError::new("Filesystem not found or MGS is not mounted", Value::null())
            })?;

        let kwargs: HashMap<String, String> =
            vec![("message".into(), "Unmounting snapshot".into())]
                .into_iter()
                .collect();

        let jobs = serde_json::json!([{
            "class_name": "UnmountSnapshotJob",
            "args": {
                "fsname": fsname,
                "name": name,
                "fqdn": active_mgs_host_fqdn,
            }
        }]);

        todo!();
    }
    #[graphql(arguments(
        fsname(description = "The filesystem to create snapshots with"),
        interval(description = "How often a snapshot should be taken"),
        use_barrier(
            description = "Set write barrier before creating snapshot. The default value is `false`"
        ),
    ))]
    /// Creates a new snapshot interval.
    /// A recurring snapshot will be taken once the given `interval` expires for the given `fsname`.
    /// In order for the snapshot to be successful, the filesystem must be available.
    async fn create_snapshot_interval(
        context: &Context,
        fsname: String,
        interval: GraphQLDuration,
        use_barrier: Option<bool>,
    ) -> juniper::FieldResult<bool> {
        let _ = fs_id_by_name(&context.pg_pool, &fsname).await?;
        let maybe_id = sqlx::query!(
            r#"
                INSERT INTO snapshot_interval (
                    filesystem_name,
                    use_barrier,
                    interval
                )
                VALUES ($1, $2, $3)
                ON CONFLICT (filesystem_name, interval)
                DO NOTHING
                RETURNING id
            "#,
            fsname,
            use_barrier.unwrap_or_default(),
            PgInterval::try_from(interval.0)?,
        )
        .fetch_optional(&context.pg_pool)
        .await?
        .map(|x| x.id);

        if let Some(id) = maybe_id {
            configure_snapshot_timer(id, fsname, interval.0, use_barrier.unwrap_or_default())
                .await?;
        }

        Ok(true)
    }
    /// Removes an existing snapshot interval.
    /// This will also cancel any outstanding intervals scheduled by this rule.
    #[graphql(arguments(id(description = "The snapshot interval id"),))]
    async fn remove_snapshot_interval(context: &Context, id: i32) -> juniper::FieldResult<bool> {
        sqlx::query!("DELETE FROM snapshot_interval WHERE id=$1", id)
            .execute(&context.pg_pool)
            .await?;

        remove_snapshot_timer(id).await?;

        Ok(true)
    }
    #[graphql(arguments(
        fsname(description = "Filesystem name"),
        reserve_value(
            description = "Delete the oldest snapshot when available space falls below this value"
        ),
        reserve_unit(description = "The unit of measurement associated with the reserve_value"),
        keep_num(
            description = "The minimum number of snapshots to keep. This is to avoid deleting all snapshots while pursuiting the reserve goal"
        )
    ))]
    /// Creates a new snapshot retention policy for the given `fsname`.
    /// Snapshots will automatically be deleted (starting with the oldest)
    /// when free space falls below the defined reserve value and its associated unit.
    async fn create_snapshot_retention(
        context: &Context,
        fsname: String,
        reserve_value: i32,
        reserve_unit: ReserveUnit,
        keep_num: Option<i32>,
    ) -> juniper::FieldResult<bool> {
        let _ = fs_id_by_name(&context.pg_pool, &fsname).await?;
        sqlx::query!(
            r#"
                INSERT INTO snapshot_retention (
                    filesystem_name,
                    reserve_value,
                    reserve_unit,
                    keep_num
                )
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (filesystem_name)
                DO UPDATE SET
                reserve_value = EXCLUDED.reserve_value,
                reserve_unit = EXCLUDED.reserve_unit,
                keep_num = EXCLUDED.keep_num
            "#,
            fsname,
            reserve_value,
            reserve_unit as ReserveUnit,
            keep_num.unwrap_or(0)
        )
        .execute(&context.pg_pool)
        .await?;

        Ok(true)
    }
    /// Remove an existing snapshot retention policy.
    #[graphql(arguments(id(description = "The snapshot retention policy id")))]
    async fn remove_snapshot_retention(context: &Context, id: i32) -> juniper::FieldResult<bool> {
        sqlx::query!("DELETE FROM snapshot_retention WHERE id=$1", id)
            .execute(&context.pg_pool)
            .await?;

        Ok(true)
    }
}

pub(crate) type Schema = RootNode<'static, QueryRoot, MutationRoot, EmptySubscription<Context>>;

pub(crate) struct Context {
    pub(crate) pg_pool: PgPool,
}

impl juniper::Context for Context {}

pub(crate) async fn graphql(
    schema: Arc<Schema>,
    ctx: Arc<Context>,
    req: GraphQLRequest,
) -> Result<impl warp::Reply, warp::Rejection> {
    let res = req.execute(&schema, &ctx).await;
    let json = serde_json::to_string(&res).map_err(EmfApiError::SerdeJsonError)?;

    Ok(json)
}

pub(crate) fn endpoint(
    schema_filter: impl Filter<Extract = (Arc<Schema>,), Error = Infallible> + Clone + Send,
    ctx_filter: impl Filter<Extract = (Arc<Context>,), Error = Infallible> + Clone + Send,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    let graphql_route = warp::path!("graphql")
        .and(warp::post())
        .and(schema_filter.clone())
        .and(ctx_filter)
        .and(warp::body::json())
        .and_then(graphql);

    let graphiql_route = warp::path!("graphiql")
        .and(warp::get())
        .map(|| warp::reply::html(graphiql_source("graphql", None)));

    let graphql_schema_route = warp::path!("graphql_schema")
        .and(warp::get())
        .and(schema_filter)
        .map(|schema: Arc<Schema>| schema.as_schema_language());

    graphql_route.or(graphiql_route).or(graphql_schema_route)
}

async fn get_fs_cluster_hosts(
    pool: &PgPool,
    fs_name: String,
) -> Result<Vec<Vec<String>>, EmfApiError> {
    let xs = get_fs_target_resources(pool, Some(fs_name))
        .await?
        .into_iter()
        .group_by(|x| x.cluster_id);

    let xs: Vec<Vec<i32>> = xs.into_iter().fold(vec![], |mut acc, (_, xs)| {
        let xs: HashSet<i32> = xs.map(|x| x.cluster_hosts).flatten().collect();

        acc.push(xs.into_iter().collect());

        acc
    });
    let xs = xs.into_iter().map(|idset| async move {
        let fqdns = idset
            .into_iter()
            .map(|x| async move { fqdn_by_host_id(pool, x).await });
        join_all(fqdns)
            .await
            .into_iter()
            .filter_map(|x| x.ok())
            .collect()
    });

    Ok(join_all(xs).await)
}

async fn get_banned_resources(pool: &PgPool) -> Result<Vec<BannedResource>, EmfApiError> {
    let xs = sqlx::query_as!(
        BannedResource,
        r#"
            SELECT * FROM corosync_resource_bans
        "#
    )
    .fetch_all(pool)
    .await?;

    Ok(xs)
}

fn validate_snapshot_name(x: &str) -> Result<(), FieldError> {
    if x.contains(' ') {
        Err(FieldError::new(
            "Snapshot name cannot contain spaces",
            Value::null(),
        ))
    } else if x.contains('*') {
        Err(FieldError::new(
            "Snapshot name cannot contain * character",
            Value::null(),
        ))
    } else if x.contains('/') {
        Err(FieldError::new(
            "Snapshot name cannot contain / character",
            Value::null(),
        ))
    } else if x.contains('&') {
        Err(FieldError::new(
            "Snapshot name cannot contain & character",
            Value::null(),
        ))
    } else {
        Ok(())
    }
}

async fn fs_id_by_name(pool: &PgPool, name: &str) -> Result<i32, juniper::FieldError> {
    sqlx::query!("SELECT id FROM filesystem WHERE name=$1", name)
        .fetch_optional(pool)
        .await?
        .map(|x| x.id)
        .ok_or_else(|| FieldError::new(format!("Filesystem {} not found", name), Value::null()))
}

async fn insert_task(
    name: &str,
    state: &str,
    single_runner: bool,
    keep_failed: bool,
    actions: &[String],
    args: serde_json::Value,
    fs_id: i32,
    pool: &PgPool,
) -> Result<Task, EmfApiError> {
    let x = sqlx::query_as!(
        Task,
        r#"
                INSERT INTO task (
                    name,
                    start,
                    state,
                    fids_total,
                    fids_completed,
                    fids_failed,
                    data_transfered,
                    single_runner,
                    keep_failed,
                    actions,
                    args,
                    filesystem_id
                )
                VALUES (
                    $1,
                    now(),
                    $2,
                    0,
                    0,
                    0,
                    0,
                    $3,
                    $4,
                    $5,
                    $6,
                    $7
                )
                RETURNING *
            "#,
        name,
        state,
        single_runner,
        keep_failed,
        actions,
        args,
        fs_id
    )
    .fetch_one(pool)
    .await?;

    Ok(x)
}

async fn insert_fidlist(fids: Vec<String>, task_id: i32, pool: &PgPool) -> Result<(), EmfApiError> {
    let x = fids
        .iter()
        .map(|fid| LustreFid::from_str(&fid))
        .filter_map(Result::ok)
        .fold((vec![], vec![], vec![]), |mut acc, fid| {
            acc.0.push(fid.seq);
            acc.1.push(fid.oid);
            acc.2.push(fid.ver);

            acc
        });

    sqlx::query!(
        r#"
	    INSERT INTO fidtaskqueue (fid, data, task_id)
            SELECT row(seq, oid, ver)::lustre_fid, '{}'::jsonb, $4
            FROM UNNEST($1::bigint[], $2::int[], $3::int[])
            AS t(seq, oid, ver)"#,
        &x.0,
        &x.1,
        &x.2,
        task_id
    )
    .execute(pool)
    .await?;

    // update the number of fids in the task
    sqlx::query!(
        r#"
        UPDATE task
        SET fids_total = fids_total + $1
        WHERE id = $2
    "#,
        fids.len() as i64,
        task_id
    )
    .execute(pool)
    .await?;

    Ok(())
}

fn create_task_job<'a>(task_id: i32) -> SendJob<'a, HashMap<String, serde_json::Value>> {
    SendJob {
        class_name: "CreateTaskJob",
        args: vec![("task_id".into(), serde_json::json!(task_id))]
            .into_iter()
            .collect(),
    }
}

async fn client_mount_source(pg_pool: &PgPool, fs_name: &str) -> Result<String, EmfApiError> {
    let nids = sqlx::query!(
        r#"
            SELECT n.nid FROM target AS t
            INNER JOIN lnet as l ON l.host_id = ANY(t.host_ids)
            INNER JOIN nid as n ON n.id = ANY(l.nids)
            WHERE t.name='MGS' AND $1 = ANY(t.filesystems)
            AND n.host_id NOT IN (
                SELECT nh.host_id
                FROM corosync_resource_bans b
                INNER JOIN corosync_node_host nh ON (nh.corosync_node_id).name = b.node
                AND nh.cluster_id = b.cluster_id
                INNER JOIN corosync_resource r ON r.name = b.resource AND b.cluster_id = r.cluster_id
                WHERE r.mount_point is not NULL AND r.mount_point = t.mount_path
            )
            GROUP BY l.host_id, n.nid ORDER BY l.host_id, n.nid
            "#,
        fs_name
    )
    .fetch_all(pg_pool)
    .await?
    .into_iter()
    .map(|x| x.nid)
    .collect::<Vec<String>>();

    let mount_command = format!("{}:/{}", nids.join(":"), fs_name);

    Ok(mount_command)
}
