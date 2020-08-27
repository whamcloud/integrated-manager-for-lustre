// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error;
use error::ImlApiError;
use futures::TryFutureExt;
use iml_action_client::invoke_rust_agent;
use iml_postgres::{sqlx, PgPool};
use iml_rabbit::Connection;
use iml_wire_types::snapshot;
use std::collections::HashMap;
use warp::Filter;

async fn active_mgs_host_fqdn(fsname: &str, pool: PgPool) -> Result<String, error::ImlApiError> {
    let mgs_id = sqlx::query!(
        r#"
        select mgs_id from chroma_core_managedfilesystem where name=$1
        "#,
        fsname
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| match e {
        sqlx::Error::RowNotFound => error::ImlApiError::FileSystemNotFound(fsname.into()),
        _ => e.into(),
    })?
    .mgs_id;

    let mgs_uuid = sqlx::query!(
        r#"
        select uuid from chroma_core_managedtarget where id=$1
        "#,
        mgs_id
    )
    .fetch_one(&pool)
    .await?
    .uuid;

    let active_mgs_host_id = sqlx::query!(
        r#"
        select active_host_id from targets where uuid=$1
        "#,
        mgs_uuid
    )
    .fetch_one(&pool)
    .await?
    .active_host_id;

    let active_mgs_host_fqdn = sqlx::query!(
        r#"
        select fqdn from chroma_core_managedhost where id=$1
        "#,
        active_mgs_host_id
    )
    .fetch_one(&pool)
    .await?
    .fqdn;

    tracing::trace!("{}", active_mgs_host_fqdn);

    Ok(active_mgs_host_fqdn)
}

async fn get_snapshots(
    args: snapshot::List,
    pool: PgPool,
) -> Result<impl warp::Reply, warp::Rejection> {
    let active_mgs_host_fqdn =
        active_mgs_host_fqdn(&args.fsname, pool)
            .await
            .map_err(|e| match e {
                error::ImlApiError::FileSystemNotFound(_) => warp::reject::not_found(),
                _ => e.into(),
            })?;

    let results = invoke_rust_agent(active_mgs_host_fqdn, "snapshot_list", args)
        .await
        .map_err(|e| ImlApiError::from(e))?;

    Ok(warp::reply::json(&results))
}

async fn create_snapshot(
    args: snapshot::Create,
    client: Connection,
    pool: PgPool,
) -> Result<impl warp::Reply, warp::Rejection> {
    let active_mgs_host_fqdn =
        active_mgs_host_fqdn(&args.fsname, pool)
            .await
            .map_err(|e| match e {
                error::ImlApiError::FileSystemNotFound(_) => warp::reject::not_found(),
                _ => e.into(),
            })?;

    let mut kwargs: HashMap<String, String> = HashMap::new();
    kwargs.insert("message".to_string(), "Creating snapshot".to_string());

    let jobs = serde_json::json!([{
        "class_name": "CreateSnapshotJob",
        "args": {
            "fsname": args.fsname,
            "name": args.name,
            "comment": args.comment,
            "fqdn": active_mgs_host_fqdn,
        }
    }]);
    let command_id: i32 =
        iml_job_scheduler_rpc::call(&client, "run_jobs", vec![jobs], Some(kwargs))
            .map_err(ImlApiError::ImlJobSchedulerRpcError)
            .await?;

    Ok(warp::reply::json(&command_id))
}

async fn destroy_snapshot(
    args: snapshot::Destroy,
    client: Connection,
    pool: PgPool,
) -> Result<impl warp::Reply, warp::Rejection> {
    let active_mgs_host_fqdn =
        active_mgs_host_fqdn(&args.fsname, pool)
            .await
            .map_err(|e| match e {
                error::ImlApiError::FileSystemNotFound(_) => warp::reject::not_found(),
                _ => e.into(),
            })?;

    let mut kwargs: HashMap<String, String> = HashMap::new();
    kwargs.insert("message".to_string(), "Destroying snapshot".to_string());

    let jobs = serde_json::json!([{
        "class_name": "DestroySnapshotJob",
        "args": {
            "fsname": args.fsname,
            "name": args.name,
            "force": args.force,
            "fqdn": active_mgs_host_fqdn,
        }
    }]);
    let command_id: i32 =
        iml_job_scheduler_rpc::call(&client, "run_jobs", vec![jobs], Some(kwargs))
            .map_err(ImlApiError::ImlJobSchedulerRpcError)
            .await?;

    Ok(warp::reply::json(&command_id))
}

async fn mount_snapshot(
    args: snapshot::Mount,
    client: Connection,
    pool: PgPool,
) -> Result<impl warp::Reply, warp::Rejection> {
    let active_mgs_host_fqdn =
        active_mgs_host_fqdn(&args.fsname, pool)
            .await
            .map_err(|e| match e {
                error::ImlApiError::FileSystemNotFound(_) => warp::reject::not_found(),
                _ => e.into(),
            })?;

    let mut kwargs: HashMap<String, String> = HashMap::new();
    kwargs.insert("message".to_string(), "Mounting snapshot".to_string());

    let jobs = serde_json::json!([{
        "class_name": "MountSnapshotJob",
        "args": {
            "fsname": args.fsname,
            "name": args.name,
            "fqdn": active_mgs_host_fqdn,
        }
    }]);
    let command_id: i32 =
        iml_job_scheduler_rpc::call(&client, "run_jobs", vec![jobs], Some(kwargs))
            .map_err(ImlApiError::ImlJobSchedulerRpcError)
            .await?;

    Ok(warp::reply::json(&command_id))
}

async fn unmount_snapshot(
    args: snapshot::Unmount,
    client: Connection,
    pool: PgPool,
) -> Result<impl warp::Reply, warp::Rejection> {
    let active_mgs_host_fqdn =
        active_mgs_host_fqdn(&args.fsname, pool)
            .await
            .map_err(|e| match e {
                error::ImlApiError::FileSystemNotFound(_) => warp::reject::not_found(),
                _ => e.into(),
            })?;

    let mut kwargs: HashMap<String, String> = HashMap::new();
    kwargs.insert("message".to_string(), "Unmounting snapshot".to_string());

    let jobs = serde_json::json!([{
        "class_name": "UnmountSnapshotJob",
        "args": {
            "fsname": args.fsname,
            "name": args.name,
            "fqdn": active_mgs_host_fqdn,
        }
    }]);
    let command_id: i32 =
        iml_job_scheduler_rpc::call(&client, "run_jobs", vec![jobs], Some(kwargs))
            .map_err(ImlApiError::ImlJobSchedulerRpcError)
            .await?;

    Ok(warp::reply::json(&command_id))
}

pub(crate) fn endpoint(
    client_filter: impl Filter<Extract = (Connection,), Error = warp::Rejection> + Clone + Send,
    pool_filter: impl Filter<Extract = (PgPool,), Error = std::convert::Infallible> + Clone + Send,
) -> impl Filter<Extract = impl warp::Reply, Error = warp::Rejection> + Clone {
    let list = warp::path!("snapshot")
        .and(warp::get())
        .and(warp::query())
        .and(pool_filter.clone())
        .and_then(get_snapshots);

    let create = warp::path!("snapshot")
        .and(warp::post())
        .and(warp::query())
        .and(client_filter.clone())
        .and(pool_filter.clone())
        .and_then(create_snapshot);

    let destroy = warp::path!("snapshot" / "destroy")
        .and(warp::post())
        .and(warp::query())
        .and(client_filter.clone())
        .and(pool_filter.clone())
        .and_then(destroy_snapshot);

    let mount = warp::path!("snapshot" / "mount")
        .and(warp::post())
        .and(warp::query())
        .and(client_filter.clone())
        .and(pool_filter.clone())
        .and_then(mount_snapshot);

    let unmount = warp::path!("snapshot" / "unmount")
        .and(warp::post())
        .and(warp::query())
        .and(client_filter.clone())
        .and(pool_filter)
        .and_then(unmount_snapshot);

    list.or(create).or(destroy).or(mount).or(unmount)
}
