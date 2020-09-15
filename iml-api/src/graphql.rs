// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{command::get_command, error::ImlApiError};
use futures::{TryFutureExt, TryStreamExt};
use iml_postgres::{sqlx, sqlx::postgres::types::PgInterval, PgPool};
use iml_rabbit::Pool;
use iml_wire_types::{snapshot::Snapshot, Command};
use itertools::Itertools;
use juniper::{
    http::{graphiql::graphiql_source, GraphQLRequest},
    EmptySubscription, FieldError, GraphQLEnum, ParseScalarResult, ParseScalarValue, RootNode,
    Value,
};
use std::ops::Deref;
use std::{
    collections::{HashMap, HashSet},
    convert::{Infallible, TryFrom as _},
    sync::Arc,
    time::Duration,
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

#[derive(juniper::GraphQLObject)]
/// A Lustre Target
struct Target {
    /// The target's state. One of "mounted" or "unmounted"
    state: String,
    /// The target name
    name: String,
    /// The `host.id` of the host running this target
    active_host_id: Option<i32>,
    /// The list of `hosts.id`s the target can be mounted on.
    ///
    /// *Note*. This list represents where the backing storage can be mounted,
    /// it does not represent any HA configuration.
    host_ids: Vec<i32>,
    /// The list of `filesystem.name`s this target belongs to.
    /// Only an `MGS` may have more than one filesystem.
    filesystems: Vec<String>,
    /// Then underlying device UUID
    uuid: String,
    /// Where this target is mounted
    mount_path: Option<String>,
}

#[derive(juniper::GraphQLObject)]
/// A Lustre Target and it's corresponding resource
struct TargetResource {
    /// The id of the cluster
    cluster_id: i32,
    /// The filesystem associated with this target
    fs_name: String,
    /// The name of this target
    name: String,
    /// The corosync resource id associated with this target
    resource_id: String,
    /// The list of host ids this target could possibly run on
    cluster_hosts: Vec<i32>,
}

struct BannedTargetResource {
    resource: String,
    cluster_id: i32,
    host_id: i32,
    mount_point: Option<String>,
}

#[derive(juniper::GraphQLObject)]
/// A Corosync banned resource
struct BannedResource {
    /// The resource id
    id: String,
    /// The id of the cluster in which the resource lives
    cluster_id: i32,
    /// The resource name
    resource: String,
    /// The node in which the resource lives
    node: String,
    /// The assigned weight of the resource
    weight: i32,
    /// Is master only
    master_only: bool,
}

// Don't need this type
#[derive(juniper::GraphQLObject)]
/// A Snapshot configuration
struct SnapshotConfiguration {
    /// The configuration id
    id: i32,
    /// The filesystem name
    filesystem_name: String,
    /// Use a write barrier
    use_barrier: bool,
    /// The interval configuration
    interval: Duration,
    /// Number of snapshots to keep
    keep_num: Option<i32>,
}

#[derive(juniper::GraphQLObject)]
struct GraphqlDuration {
    value: f64,
    unit: GraphqlDurationUnit,
}

#[derive(juniper::GraphQLEnum)]
enum GraphqlDurationUnit {
    Minutes,
    Hours,
    Days,
    Weeks,
}

impl From<GraphqlDuration> for Duration {
    fn from(x: GraphqlDuration) -> Self {
        match x.unit {
            GraphqlDurationUnit::Minutes => Self::from_secs_f64(x.value * 60.0f64),
            GraphqlDurationUnit::Hours => Self::from_secs_f64(x.value * 60.0f64 * 60.0f64),
            GraphqlDurationUnit::Days => Self::from_secs_f64(x.value * 60.0f64 * 60.0f64 * 24.0f64),
            GraphqlDurationUnit::Weeks => {
                Self::from_secs_f64(x.value * 60.0f64 * 60.0f64 * 24.0f64 * 7.0f64)
            }
        }
    }
}

impl From<Duration> for GraphqlDuration {
    fn from(x: Duration) -> Self {
        Self {
            value: (x.as_secs() as f64 / 60.0f64).floor(),
            unit: GraphqlDurationUnit::Minutes,
        }
    }
}

#[derive(juniper::GraphQLObject)]
struct SnapshotRetention {
    id: i32,
    delete_when: DeleteWhen,
}

pub(crate) struct QueryRoot;
pub(crate) struct MutationRoot;

#[derive(GraphQLEnum)]
enum SortDir {
    Asc,
    Desc,
}

impl Default for SortDir {
    fn default() -> Self {
        Self::Asc
    }
}

impl Deref for SortDir {
    type Target = str;

    fn deref(&self) -> &Self::Target {
        match self {
            Self::Asc => "asc",
            Self::Desc => "desc",
        }
    }
}

#[juniper::graphql_object(Context = Context)]
impl QueryRoot {
    #[graphql(arguments(
        limit(description = "paging limit, defaults to 20"),
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
                    CASE WHEN $1 = 'asc' THEN n.id END ASC,
                    CASE WHEN $1 = 'desc' THEN n.id END DESC
                OFFSET $2 LIMIT $3"#,
            dir.deref(),
            offset.unwrap_or(0) as i64,
            limit.unwrap_or(20) as i64
        )
        .fetch_all(&context.pg_pool)
        .await?;

        Ok(xs)
    }

    #[graphql(arguments(
        limit(description = "paging limit, defaults to 20"),
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
    ) -> juniper::FieldResult<Vec<Target>> {
        let dir = dir.unwrap_or_default();

        let xs: Vec<Target> = sqlx::query_as!(
            Target,
            r#"
                SELECT * from target t
                ORDER BY
                    CASE WHEN $3 = 'asc' THEN t.name END ASC,
                    CASE WHEN $3 = 'desc' THEN t.name END DESC
                OFFSET $1 LIMIT $2"#,
            offset.unwrap_or(0) as i64,
            limit.unwrap_or(20) as i64,
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

        let xs: Vec<Target> = xs
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
    #[graphql(arguments(fs_name(description = "The filesystem to search cluster nodes for"),))]
    async fn get_fs_cluster_hosts(
        context: &Context,
        fs_name: String,
    ) -> juniper::FieldResult<Vec<Vec<i32>>> {
        let xs = get_fs_target_resources(&context.pg_pool, Some(fs_name))
            .await?
            .into_iter()
            .group_by(|x| x.cluster_id);

        let xs = xs.into_iter().fold(vec![], |mut acc, (_, xs)| {
            let xs: HashSet<i32> = xs.map(|x| x.cluster_hosts).flatten().collect();

            acc.push(xs.into_iter().collect());

            acc
        });

        Ok(xs)
    }
    #[graphql(arguments(
        limit(description = "paging limit, defaults to 20"),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to asc"),
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

        let snapshots = sqlx::query_as!(
            Snapshot,
                r#"
                    SELECT filesystem_name, snapshot_name, create_time, modify_time, snapshot_fsname, mounted, comment FROM snapshot s
                    WHERE filesystem_name = $4 AND ($5::text IS NULL OR snapshot_name = $5)
                    ORDER BY
                        CASE WHEN $3 = 'asc' THEN s.create_time END ASC,
                        CASE WHEN $3 = 'desc' THEN s.create_time END DESC
                    OFFSET $1 LIMIT $2"#,
                offset.unwrap_or(0) as i64,
                limit.unwrap_or(20) as i64,
                dir.deref(),
                fsname,
                name,
            )
            .fetch_all(&context.pg_pool)
            .await?;

        Ok(snapshots)
    }
}

#[juniper::graphql_object(Context = Context)]
impl MutationRoot {
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
        let name = name.trim();
        validate_snapshot_name(name)?;

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
        let command_id: i32 = iml_job_scheduler_rpc::call(
            &context.rabbit_pool.get().await?,
            "run_jobs",
            vec![jobs],
            Some(kwargs),
        )
        .map_err(ImlApiError::ImlJobSchedulerRpcError)
        .await?;

        let command = get_command(&context.pg_pool, command_id).await?;

        Ok(command)
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
        let command_id: i32 = iml_job_scheduler_rpc::call(
            &context.rabbit_pool.get().await?,
            "run_jobs",
            vec![jobs],
            Some(kwargs),
        )
        .map_err(ImlApiError::ImlJobSchedulerRpcError)
        .await?;

        let command = get_command(&context.pg_pool, command_id).await?;

        Ok(command)
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
        let command_id: i32 = iml_job_scheduler_rpc::call(
            &context.rabbit_pool.get().await?,
            "run_jobs",
            vec![jobs],
            Some(kwargs),
        )
        .map_err(ImlApiError::ImlJobSchedulerRpcError)
        .await?;

        get_command(&context.pg_pool, command_id)
            .await
            .map_err(|e| e.into())
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
        let command_id: i32 = iml_job_scheduler_rpc::call(
            &context.rabbit_pool.get().await?,
            "run_jobs",
            vec![jobs],
            Some(kwargs),
        )
        .map_err(ImlApiError::ImlJobSchedulerRpcError)
        .await?;

        get_command(&context.pg_pool, command_id)
            .await
            .map_err(|e| e.into())
    }

    /// Creates a new snapshot interval configuration in the database and registers the interval with the timer.
    /// The interval is in seconds.
    async fn configure_snapshot(
        context: &Context,
        fsname: String,
        use_barrier: Option<bool>,
        interval: GraphqlDuration,
        keep_num: Option<i32>,
        delete_when: DeleteWhen,
    ) -> juniper::FieldResult<String> {
        sqlx::query!(
            r#"
                INSERT INTO snapshot_configuration (
                    filesystem_name,
                    use_barrier,
                    interval,
                    keep_num
                )
                VALUES ($1, $2, $3, $4)
            "#,
            fsname,
            use_barrier.unwrap_or_default(),
            PgInterval::try_from(interval.into())?,
            keep_num,
        )
        .execute(&context.pg_pool)
        .await?;

        Ok("complete".to_string())
    }

    async fn list_snapshots(context: &Context) -> juniper::FieldResult<String> {
        let xs: Vec<SnapshotConfiguration> = sqlx::query!(
            r#"
                SELECT id, filesystem_name, use_barrier, interval as 'interval:GraphqlDuration', keep_num
                FROM snapshot_configuration 
            "#
        )
        .fetch(&context.pg_pool)
        .map_ok(|x| {
            SnapshotConfiguration {
                id: x.id,
                filesystem_name: x.filesystem_name,
                use_barrier: x.use_barrier,
                interval: x.interval,
                keep_num: x.keep_num,
            }
        })
        .try_collect()
        .await?;

        Ok("complete".to_string())
    }
}

#[derive(serde::Deserialize, juniper::GraphQLEnum)]
enum IntervalUnit {
    Hours,
    Days,
}
#[derive(juniper::GraphQLInputObject)]
struct Interval {
    value: i32,
    unit: IntervalUnit,
}

#[derive(juniper::GraphQLObject)]
struct DeleteWhen {
    value: i32,
    unit: DeleteUnit,
}

#[sqlx(rename = "snapshot_delete_unit")]
#[derive(serde::Deserialize, juniper::GraphQLEnum, Debug, sqlx::Type)]
enum DeleteUnit {
    Percent,
    Gibibytes,
    Tebibytes,
}

impl ToString for DeleteUnit {
    fn to_string(&self) -> String {
        match self {
            Self::Percent => "percent".to_string(),
            Self::Gibibytes => "gibibytes".to_string(),
            Self::Tebibytes => "tebibytes".to_string(),
        }
    }
}

impl From<Option<String>> for DeleteUnit {
    fn from(unit: Option<String>) -> Self {
        if let Some(unit) = unit {
            match unit.as_str() {
                "percent" => Self::Percent,
                "gibibytes" => Self::Gibibytes,
                "tebibytes" => Self::Tebibytes,
            }
        } else {
            Self::Percent
        }
    }
}

async fn active_mgs_host_fqdn(
    fsname: &str,
    pool: &PgPool,
) -> Result<Option<String>, iml_postgres::sqlx::Error> {
    let fsnames = &[fsname.into()][..];
    let maybe_active_mgs_host_id = sqlx::query!(
        r#"
            SELECT active_host_id from target WHERE filesystems @> $1 and name='MGS'
        "#,
        fsnames
    )
    .fetch_optional(pool)
    .await?
    .and_then(|x| x.active_host_id);

    tracing::trace!("Maybe active MGS host id: {:?}", maybe_active_mgs_host_id);

    if let Some(active_mgs_host_id) = maybe_active_mgs_host_id {
        let active_mgs_host_fqdn = sqlx::query!(
            r#"
                SELECT fqdn FROM chroma_core_managedhost WHERE id=$1 and not_deleted = 't'
            "#,
            active_mgs_host_id
        )
        .fetch_one(pool)
        .await?
        .fqdn;

        Ok(Some(active_mgs_host_fqdn))
    } else {
        Ok(None)
    }
}

pub(crate) type Schema = RootNode<'static, QueryRoot, MutationRoot, EmptySubscription<Context>>;

pub(crate) struct Context {
    pub(crate) pg_pool: PgPool,
    pub(crate) rabbit_pool: Pool,
}

pub(crate) async fn graphql(
    schema: Arc<Schema>,
    ctx: Arc<Context>,
    req: GraphQLRequest,
) -> Result<impl warp::Reply, warp::Rejection> {
    let res = req.execute(&schema, &ctx).await;
    let json = serde_json::to_string(&res).map_err(ImlApiError::SerdeJsonError)?;

    Ok(json)
}

pub(crate) fn endpoint(
    schema_filter: impl Filter<Extract = (Arc<Schema>,), Error = Infallible> + Clone + Send,
    ctx_filter: impl Filter<Extract = (Arc<Context>,), Error = Infallible> + Clone + Send,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    let graphql_route = warp::path!("graphql")
        .and(warp::post())
        .and(schema_filter)
        .and(ctx_filter)
        .and(warp::body::json())
        .and_then(graphql);

    let graphiql_route = warp::path!("graphiql")
        .and(warp::get())
        .map(|| warp::reply::html(graphiql_source("graphql", None)));

    graphql_route.or(graphiql_route)
}

async fn get_fs_target_resources(
    pool: &PgPool,
    fs_name: Option<String>,
) -> Result<Vec<TargetResource>, ImlApiError> {
    let banned_resources = get_banned_targets(pool).await?;

    let xs = sqlx::query!(r#"
            SELECT rh.cluster_id, r.id, t.name, t.mount_path, t.filesystems, array_agg(DISTINCT rh.host_id) AS "cluster_hosts!"
            FROM target t
            INNER JOIN corosync_target_resource r ON r.mount_point = t.mount_path
            INNER JOIN corosync_target_resource_managed_host rh ON rh.corosync_resource_id = r.id AND rh.host_id = ANY(t.host_ids)
            WHERE CARDINALITY(t.filesystems) > 0
            GROUP BY rh.cluster_id, t.name, r.id, t.mount_path, t.filesystems
        "#)
            .fetch(pool)
            .try_filter(|x| {
                let fs_name2 = fs_name.clone();
                let filesystems = x.filesystems.clone();
                async move {
                    match fs_name2 {
                        None => true,
                        Some(fs) => filesystems.contains(&fs)
                    }
                }
            })
            .map_ok(|mut x| {
                let xs:HashSet<_> = banned_resources
                    .iter()
                    .filter(|y| {
                        y.cluster_id == x.cluster_id && y.resource == x.id &&  x.mount_path == y.mount_point
                    })
                    .map(|y| y.host_id)
                    .collect();

                x.cluster_hosts.retain(|id| !xs.contains(id));

                x
            })
            .map_ok(|x| {
                TargetResource {
                    cluster_id: x.cluster_id,
                    fs_name: fs_name.as_ref().unwrap_or_else(|| &x.filesystems[0]).to_string(),
                    name: x.name,
                    resource_id: x.id,
                    cluster_hosts: x.cluster_hosts
                }
            }).try_collect()
            .await?;

    Ok(xs)
}

async fn get_banned_targets(pool: &PgPool) -> Result<Vec<BannedTargetResource>, ImlApiError> {
    let xs = sqlx::query!(r#"
            SELECT b.id, b.resource, b.node, b.cluster_id, nh.host_id, t.mount_point
            FROM corosync_resource_bans b
            INNER JOIN corosync_node_managed_host nh ON (nh.corosync_node_id).name = b.node
            AND nh.cluster_id = b.cluster_id
            INNER JOIN corosync_target_resource t ON t.id = b.resource AND b.cluster_id = t.cluster_id
        "#)
        .fetch(pool)
        .map_ok(|x| {
            BannedTargetResource {
                resource: x.resource,
                cluster_id: x.cluster_id,
                host_id: x.host_id,
                mount_point: x.mount_point,
            }
        })
        .try_collect()
        .await?;

    Ok(xs)
}

async fn get_banned_resources(pool: &PgPool) -> Result<Vec<BannedResource>, ImlApiError> {
    let xs = sqlx::query_as!(
        BannedResource,
        r#"
            SELECT id, cluster_id, resource, node, weight, master_only
            FROM corosync_resource_bans
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
    } else if x.contains("&") {
        Err(FieldError::new(
            "Snapshot name cannot contain & character",
            Value::null(),
        ))
    } else {
        Ok(())
    }
}
