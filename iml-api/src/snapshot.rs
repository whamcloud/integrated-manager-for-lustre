// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error;
use iml_action_client::invoke_rust_agent;
use iml_postgres::{sqlx, PgPool};
use iml_rabbit::Connection;
use iml_wire_types::snapshot;
use warp::{reply::Json, Filter};

async fn get_snapshots_internal(
    args: snapshot::List,
    conn: Connection,
    pool: PgPool,
) -> Result<(), error::ImlApiError> {
    drop(conn);

    let mgs_id = sqlx::query!(
        r#"
        select mgs_id from chroma_core_managedfilesystem where name=$1
        "#,
        args.fsname
    )
    .fetch_one(&pool)
    .await?
    .mgs_id;

    let mgs = sqlx::query!(
        r#"
        select * from chroma_core_managedtarget where id=$1
        "#,
        mgs_id
    )
    .fetch_one(&pool)
    .await?;

    Ok(())
}

async fn get_snapshots(
    args: snapshot::List,
    conn: Connection,
    pool: PgPool,
) -> Result<impl warp::Reply, warp::Rejection> {
    let snapshots = get_snapshots_internal(args, conn, pool).await?;

    Ok(warp::reply::json(&snapshots))
}

pub(crate) fn endpoint(
    client_filter: impl Filter<Extract = (Connection,), Error = warp::Rejection> + Clone + Send,
    pool_filter: impl Filter<Extract = (PgPool,), Error = std::convert::Infallible> + Clone + Send,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    warp::path!("snapshot" / "list")
        .and(warp::query())
        .and(warp::get())
        .and(client_filter)
        .and(pool_filter)
        .and_then(get_snapshots)
}
