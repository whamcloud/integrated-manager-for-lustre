// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::ImlApiError;
use iml_action_client::invoke_rust_agent;
use iml_postgres::{sqlx, PgPool};
use juniper::{
    http::{graphiql::graphiql_source, GraphQLRequest},
    EmptyMutation, EmptySubscription, GraphQLEnum, RootNode,
};
use sqlx::types::chrono::{DateTime, Utc};
use std::ops::Deref;
use std::{convert::Infallible, sync::Arc};
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

#[derive(juniper::GraphQLEnum, juniper::serde::Deserialize)]
enum Status {
    Mounted,
    NotMounted,
}

#[derive(juniper::GraphQLObject, juniper::serde::Deserialize)]
struct Detail {
    /// E. g. MDT0000
    pub role: Option<String>,
    /// Filesystem id (random string)
    pub fsname: String,
    pub modify_time: DateTime<Utc>,
    pub create_time: DateTime<Utc>,
    /// Snapshot status (None means unknown)
    pub status: Option<Status>,
    /// Optional comment for the snapshot
    pub comment: Option<String>,
}

#[derive(juniper::GraphQLObject, juniper::serde::Deserialize)]
/// A snapshot
struct Snapshot {
    /// Filesystem name
    pub fsname: String,
    /// Snapshot name
    pub name: String,
    /// Snapshot members
    pub details: Vec<Detail>,
}

#[derive(juniper::GraphQLInputObject, juniper::serde::Serialize)]
pub struct List {
    /// Filesystem name
    pub fsname: String,
    /// Name of the snapshot to list
    pub name: Option<String>,

    /// List details
    pub detail: bool,
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
        .fetch_all(&context.client)
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
                SELECT * from targets t
                ORDER BY
                    CASE WHEN $3 = 'asc' THEN t.name END ASC,
                    CASE WHEN $3 = 'desc' THEN t.name END DESC
                OFFSET $1 LIMIT $2"#,
            offset.unwrap_or(0) as i64,
            limit.unwrap_or(20) as i64,
            dir.deref()
        )
        .fetch_all(&context.client)
        .await?;

        Ok(xs)
    }
    #[graphql(arguments(
        limit(description = "paging limit, defaults to 20"),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to asc"),
        args(description = "Snapshot listing arguments")
    ))]
    /// Fetch the list of snapshots
    async fn snapshots(
        context: &Context,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
        args: List,
    ) -> juniper::FieldResult<Vec<Snapshot>> {
        let dir = dir.unwrap_or_default();

        let active_mgs_host_fqdn = active_mgs_host_fqdn(&args.fsname, &context.client)
            .await
            .unwrap();

        let results = invoke_rust_agent(active_mgs_host_fqdn, "snapshot_list", args)
            .await
            .map_err(|e| ImlApiError::from(e))?;

        let result: Result<Vec<Snapshot>, String> = serde_json::from_value(results)?;

        let result = result.unwrap();

        Ok(result)
    }
}

async fn active_mgs_host_fqdn(fsname: &str, pool: &PgPool) -> Result<String, ()> {
    let mgs_id = sqlx::query!(
        r#"
        select mgs_id from chroma_core_managedfilesystem where name=$1
        "#,
        fsname
    )
    .fetch_one(pool)
    .await
    .map_err(|e| ())?
    .mgs_id;

    let mgs_uuid = sqlx::query!(
        r#"
        select uuid from chroma_core_managedtarget where id=$1
        "#,
        mgs_id
    )
    .fetch_one(pool)
    .await
    .map_err(|e| ())?
    .uuid;

    let active_mgs_host_id = sqlx::query!(
        r#"
        select active_host_id from targets where uuid=$1
        "#,
        mgs_uuid
    )
    .fetch_one(pool)
    .await
    .map_err(|e| ())?
    .active_host_id;

    let active_mgs_host_fqdn = sqlx::query!(
        r#"
        select fqdn from chroma_core_managedhost where id=$1
        "#,
        active_mgs_host_id
    )
    .fetch_one(pool)
    .await
    .map_err(|e| ())?
    .fqdn;

    tracing::trace!("{}", active_mgs_host_fqdn);

    Ok(active_mgs_host_fqdn)
}

pub(crate) type Schema =
    RootNode<'static, QueryRoot, EmptyMutation<Context>, EmptySubscription<Context>>;

pub(crate) struct Context {
    pub(crate) client: PgPool,
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
