// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{command::get_command, error::ImlApiError};
use futures::TryFutureExt;
use iml_postgres::{sqlx, PgPool};
use iml_rabbit::Pool;
use iml_wire_types::{
    snapshot::{Detail, Snapshot, Status},
    Command,
};
use juniper::{
    http::{graphiql::graphiql_source, GraphQLRequest},
    EmptyMutation, EmptySubscription, FieldError, GraphQLEnum, RootNode, Value,
};
use std::ops::Deref;
use std::{collections::HashMap, convert::Infallible, sync::Arc};
use warp::Filter;

#[derive(juniper::GraphQLObject)]
/// A Corosync Node found in `crm_mon`
struct CorosyncNode {
    /// The name of the node
    name: String,
    /// The id of the node as reported by `crm_mon`
    id: String,
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

pub(crate) struct QueryRoot;

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
                SELECT * FROM corosync_node n
                ORDER BY
                    CASE WHEN $3 = 'asc' THEN (n.id, n.name) END ASC,
                    CASE WHEN $3 = 'desc' THEN (n.id, n.name) END DESC
                OFFSET $1 LIMIT $2"#,
            offset.unwrap_or(0) as i64,
            limit.unwrap_or(20) as i64,
            dir.deref()
        )
        .fetch_all(&context.pg_pool)
        .await?;

        Ok(xs)
    }
    #[graphql(arguments(
        limit(description = "paging limit, defaults to 20"),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to asc")
    ))]
    /// Fetch the list of known targets
    async fn targets(
        context: &Context,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
    ) -> juniper::FieldResult<Vec<Target>> {
        let dir = dir.unwrap_or_default();

        let xs = sqlx::query_as!(
            Target,
            r#"
                SELECT * FROM targets t
                ORDER BY
                    CASE WHEN $3 = 'asc' THEN t.name END ASC,
                    CASE WHEN $3 = 'desc' THEN t.name END DESC
                OFFSET $1 LIMIT $2"#,
            offset.unwrap_or(0) as i64,
            limit.unwrap_or(20) as i64,
            dir.deref()
        )
        .fetch_all(&context.pg_pool)
        .await?;

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

        let xs = sqlx::query!(
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

        let snapshots: Vec<_> = xs
            .into_iter()
            .map(|x| Snapshot {
                snapshot_name: x.snapshot_name,
                filesystem_name: x.filesystem_name,
                details: vec![Detail {
                    comment: x.comment,
                    create_time: x.create_time,
                    modify_time: x.modify_time,
                    snapshot_fsname: x.snapshot_fsname,
                    snapshot_role: None,
                    status: x.mounted.map(|b| {
                        if b {
                            Status::Mounted
                        } else {
                            Status::NotMounted
                        }
                    }),
                }],
            })
            .collect();

        Ok(snapshots)
    }
    #[graphql(arguments(
        fsname(description = "Filesystem to take snapshot from"),
        name(description = "Name of the snapshot"),
        comment(description = "Comment for the snapshot"),
    ))]
    async fn create_snapshot(
        context: &Context,
        fsname: String,
        name: String,
        comment: Option<String>,
    ) -> juniper::FieldResult<Command> {
        let active_mgs_host_fqdn = active_mgs_host_fqdn(&fsname, &context.pg_pool)
            .await?
            .ok_or(FieldError::new(
                "Filesystem not found or MGS is not mounted",
                Value::null(),
            ))?;

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
        force(description = "Whether to force the removal"),
    ))]
    async fn destroy_snapshot(
        context: &Context,
        fsname: String,
        name: String,
        force: bool,
    ) -> juniper::FieldResult<Command> {
        let active_mgs_host_fqdn = active_mgs_host_fqdn(&fsname, &context.pg_pool)
            .await?
            .ok_or(FieldError::new(
                "Filesystem not found or MGS is not mounted",
                Value::null(),
            ))?;

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
    async fn mount_snapshot(
        context: &Context,
        fsname: String,
        name: String,
    ) -> juniper::FieldResult<Command> {
        let active_mgs_host_fqdn = active_mgs_host_fqdn(&fsname, &context.pg_pool)
            .await?
            .ok_or(FieldError::new(
                "Filesystem not found or MGS is not mounted",
                Value::null(),
            ))?;

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
    async fn unmount_snapshot(
        context: &Context,
        fsname: String,
        name: String,
    ) -> juniper::FieldResult<Command> {
        let active_mgs_host_fqdn = active_mgs_host_fqdn(&fsname, &context.pg_pool)
            .await?
            .ok_or(FieldError::new(
                "Filesystem not found or MGS is not mounted",
                Value::null(),
            ))?;

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
}

async fn active_mgs_host_fqdn(
    fsname: &str,
    pool: &PgPool,
) -> Result<Option<String>, iml_postgres::sqlx::Error> {
    let fsnames = &[fsname.into()][..];
    let maybe_active_mgs_host_id_row = sqlx::query!(
        r#"
            select active_host_id from targets where filesystems @> $1 and name='MGS'
            "#,
        fsnames
    )
    .fetch_optional(pool)
    .await?;

    tracing::trace!(
        "Maybe active MGS host id row: {:?}",
        maybe_active_mgs_host_id_row
    );

    if let Some(active_mgs_host_id_row) = maybe_active_mgs_host_id_row {
        let maybe_active_mgs_host_id = active_mgs_host_id_row.active_host_id;
        if let Some(active_mgs_host_id) = maybe_active_mgs_host_id {
            let active_mgs_host_fqdn = sqlx::query!(
                r#"
                    select fqdn from chroma_core_managedhost where id=$1 and not_deleted = 't'
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
    } else {
        Ok(None)
    }
}

pub(crate) type Schema =
    RootNode<'static, QueryRoot, EmptyMutation<Context>, EmptySubscription<Context>>;

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
