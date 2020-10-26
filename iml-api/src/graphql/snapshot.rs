// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.
use crate::{
    command::get_command,
    error::ImlApiError,
    graphql::{fs_id_by_name, Context},
};
use futures::{TryFutureExt, TryStreamExt};
use iml_postgres::{active_mgs_host_fqdn, sqlx, sqlx::postgres::types::PgInterval};
use iml_wire_types::{
    graphql_duration::GraphQLDuration,
    snapshot::{Snapshot, SnapshotPolicy},
    Command, SortDir,
};
use juniper::{FieldError, Value};
use std::{collections::HashMap, convert::TryFrom as _, ops::Deref};

pub(crate) struct SnapshotQuery;

#[juniper::graphql_object(Context = Context)]
impl SnapshotQuery {
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

    /// List automatic snapshot policies.
    async fn snapshot_policies(context: &Context) -> juniper::FieldResult<Vec<SnapshotPolicy>> {
        let xs = sqlx::query!(r#"SELECT * FROM snapshot_policy"#)
            .fetch(&context.pg_pool)
            .map_ok(|x| SnapshotPolicy {
                id: x.id,
                filesystem: x.filesystem,
                interval: x.interval.into(),
                barrier: x.barrier,
                keep: x.keep,
                daily: x.daily,
                weekly: x.weekly,
                monthly: x.monthly,
                last_run: x.last_run,
            })
            .try_collect()
            .await?;

        Ok(xs)
    }
}

pub(crate) struct SnapshotMutation;

#[juniper::graphql_object(Context = Context)]
impl SnapshotMutation {
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
        let _ = fs_id_by_name(&context.pg_pool, &fsname).await?;
        let name = name.trim();
        validate_snapshot_name(name)?;

        let fqdn = active_mgs_host_fqdn(&fsname, &context.pg_pool)
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
                "fqdn": fqdn,
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
        filesystem(description = "The filesystem to create snapshots with"),
        interval(description = "How often a snapshot should be taken"),
        use_barrier(
            description = "Set write barrier before creating snapshot. The default value is `false`"
        ),
        keep(description = "Number of the most recent snapshots to keep"),
        daily(description = "The number of days when keep the most recent snapshot of each day"),
        weekly(
            description = "The number of weeks when keep the most recent snapshot of each week"
        ),
        monthly(
            description = "The number of months when keep the most recent snapshot of each month"
        ),
    ))]
    /// Create an automatic snapshot policy.
    async fn create_snapshot_policy(
        context: &Context,
        filesystem: String,
        interval: GraphQLDuration,
        barrier: Option<bool>,
        keep: i32,
        daily: Option<i32>,
        weekly: Option<i32>,
        monthly: Option<i32>,
    ) -> juniper::FieldResult<bool> {
        sqlx::query!(
            r#"
                INSERT INTO snapshot_policy (
                    filesystem,
                    interval,
                    barrier,
                    keep,
                    daily,
                    weekly,
                    monthly
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (filesystem)
                DO UPDATE SET
                    interval = EXCLUDED.interval,
                    barrier = EXCLUDED.barrier,
                    keep = EXCLUDED.keep,
                    daily = EXCLUDED.daily,
                    weekly = EXCLUDED.weekly,
                    monthly = EXCLUDED.monthly
            "#,
            filesystem,
            PgInterval::try_from(interval.0)?,
            barrier.unwrap_or(false),
            keep,
            daily.unwrap_or(0),
            weekly.unwrap_or(0),
            monthly.unwrap_or(0)
        )
        .execute(&context.pg_pool)
        .await?;

        Ok(true)
    }

    #[graphql(arguments(filesystem(
        description = "The filesystem to remove snapshot policies for"
    ),))]
    /// Removes the automatic snapshot policy.
    async fn remove_snapshot_policy(
        context: &Context,
        filesystem: String,
    ) -> juniper::FieldResult<bool> {
        sqlx::query!(
            "DELETE FROM snapshot_policy WHERE filesystem = $1",
            filesystem
        )
        .execute(&context.pg_pool)
        .await?;

        Ok(true)
    }
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
