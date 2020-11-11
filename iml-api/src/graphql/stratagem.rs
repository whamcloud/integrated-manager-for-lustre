// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    command::get_command,
    error::ImlApiError,
    graphql::{fs_id_by_name, insert_task, Context, SendJob},
};
use futures::{
    future::{self, try_join_all},
    TryFutureExt, TryStreamExt,
};
use iml_manager_env::get_report_path;
use iml_postgres::{sqlx, PgPool};
use iml_wire_types::{
    graphql_duration::GraphQLDuration, stratagem, task::TaskArgs, Command, HotpoolConfiguration,
    SortDir, StratagemReport,
};
use juniper::{FieldError, Value};
use std::{collections::HashMap, ops::Deref};
use tokio::fs;
use uuid::Uuid;

pub(crate) struct StratagemQuery;

#[derive(Debug, juniper::GraphQLEnum)]
enum HotpoolState {
    Unconfigured,
    Configured,
    Stopped,
    Started,
    Removed,
}

impl std::fmt::Display for HotpoolState {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Self::Unconfigured => f.pad(&format!("{}", "unconfigured")),
            Self::Configured => f.pad(&format!("{}", "configured")),
            Self::Stopped => f.pad(&format!("{}", "stopped")),
            Self::Started => f.pad(&format!("{}", "started")),
            Self::Removed => f.pad(&format!("{}", "removed")),
        }
    }
}

#[juniper::graphql_object(Context = Context)]
impl StratagemQuery {
    #[graphql(arguments(
        limit(description = "paging limit, defaults to 20"),
        offset(description = "Offset into items, defaults to 0"),
        dir(description = "Sort direction, defaults to asc"),
    ))]
    /// Fetch the list of known targets
    async fn hotpools(
        context: &Context,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
    ) -> juniper::FieldResult<Vec<HotpoolConfiguration>> {
        let dir = dir.unwrap_or_default();

        let xs: Vec<HotpoolConfiguration> = sqlx::query_as!(
            HotpoolConfiguration,
            r#"
                SELECT h.id, f.name AS filesystem, h.state, h.state_modified_at, h.ha_label,
                hp.name AS hot_pool, cp.name AS cold_pool, a.extend_id, a.resync_id, a.minage, p.purge_id,
                h.version::integer as "version: i32",
                p.freehi::integer as "freehi: i32",
                p.freelo::integer as "freelo: i32"
                FROM chroma_core_hotpoolconfiguration h
                JOIN chroma_core_managedfilesystem f ON h.filesystem_id = f.id
                JOIN chroma_core_lamigoconfiguration a ON h.id = a.hotpool_id
                JOIN chroma_core_lpurgeconfiguration p ON h.id = p.hotpool_id
                JOIN chroma_core_ostpool cp ON a.cold_id = cp.id
                JOIN chroma_core_ostpool hp ON a.hot_id = hp.id
                WHERE h.not_deleted = 't'
                ORDER BY
                    CASE WHEN $3 = 'asc' THEN h.id END ASC,
                    CASE WHEN $3 = 'desc' THEN h.id END DESC
                OFFSET $1 LIMIT $2"#,
            offset.unwrap_or(0) as i64,
            limit.unwrap_or(20) as i64,
            dir.deref()
        )
        .fetch_all(&context.pg_pool)
        .await?
        .into_iter()
        .collect();

        Ok(xs)
    }

    /// List completed Stratagem reports that currently reside on the manager node.
    /// Note: All report names must be valid unicode.
    async fn stratagem_reports(_context: &Context) -> juniper::FieldResult<Vec<StratagemReport>> {
        let paths = tokio::fs::read_dir(get_report_path()).await?;

        let file_paths = paths
            .map_ok(|x| x.file_name().to_string_lossy().to_string())
            .try_collect::<Vec<String>>()
            .await?
            .into_iter()
            .map(|filename| {
                fs::canonicalize(get_report_path().join(filename.clone()))
                    .map_ok(|file_path| (file_path, filename))
            });

        let items = try_join_all(file_paths)
            .await?
            .into_iter()
            .map(|(file_path, filename)| (file_path.to_string_lossy().to_string(), filename))
            .map(get_stratagem_files);

        let items = try_join_all(items).await?;

        Ok(items)
    }
}

pub(crate) struct StratagemMutation;

#[juniper::graphql_object(Context = Context)]
impl StratagemMutation {
    async fn run_filesync(
        context: &Context,
        fsname: String,
        remote: String,
        expression: String,
        action: String,
    ) -> juniper::FieldResult<Command> {
        let uuid = Uuid::new_v4().to_hyphenated().to_string();

        let fs_id = fs_id_by_name(&context.pg_pool, &fsname).await?;

        let task = insert_task(
            &format!("{}-filesync-filesync", uuid),
            "created",
            false,
            false,
            &vec!["stratagem.filesync".into()],
            serde_json::json!({
                "remote": remote,
                "expression": expression,
                "action": action,
            }),
            fs_id,
            &context.pg_pool,
        )
        .await?;

        let mut jobs: Vec<SendJob<HashMap<String, serde_json::Value>>> = vec![SendJob {
            class_name: "CreateTaskJob".into(),
            args: vec![("task_id".into(), serde_json::json!(task.id))]
                .into_iter()
                .collect(),
        }];

        let job_range: Vec<_> = (0..jobs.len()).collect();

        let xs = get_target_hosts_by_fsname(&fsname, &context.pg_pool).await?;

        for x in xs {
            let path = match x.dev_path {
                Some(x) => x,
                None => continue,
            };

            let cfg = stratagem::StratagemConfig {
                flist_type: "none".into(),
                summarize_size: true,
                device: stratagem::StratagemDevice {
                    path,
                    groups: vec!["filesync".into()],
                },
                groups: vec![stratagem::StratagemGroup {
                    name: "filesync".into(),
                    rules: vec![stratagem::StratagemRule {
                        action: "LAT_SHELL_CMD_FID".into(),
                        expression: expression.clone(),
                        argument: "filesync".into(),
                        counter_name: Some("filesync".into()),
                    }],
                }],
            };

            jobs.push(SendJob {
                class_name: "ScanMdtJob".into(),
                args: vec![
                    ("fqdn".into(), serde_json::to_value(&x.fqdn)?),
                    ("uuid".into(), serde_json::to_value(&uuid)?),
                    ("fsname".into(), serde_json::to_value(&fsname)?),
                    ("config".into(), serde_json::to_value(cfg)?),
                    (
                        "depends_on_job_range".into(),
                        serde_json::to_value(&job_range)?,
                    ),
                ]
                .into_iter()
                .collect(),
            })
        }

        let kwargs: HashMap<String, String> =
            vec![("message".into(), "Stratagem: Filesync".into())]
                .into_iter()
                .collect();

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
    async fn run_cloudsync(
        context: &Context,
        fsname: String,
        remote: String,
        expression: String,
        action: String,
    ) -> juniper::FieldResult<Command> {
        let uuid = Uuid::new_v4().to_hyphenated().to_string();

        let fs_id = fs_id_by_name(&context.pg_pool, &fsname).await?;

        let task = insert_task(
            &format!("{}-cloudsync-cloudsync", uuid),
            "created",
            false,
            false,
            &vec!["stratagem.cloudsync".into()],
            serde_json::json!({
                "remote": remote,
                "expression": expression,
                "action": action,
            }),
            fs_id,
            &context.pg_pool,
        )
        .await?;

        let mut jobs: Vec<SendJob<HashMap<String, serde_json::Value>>> = vec![SendJob {
            class_name: "CreateTaskJob".into(),
            args: vec![("task_id".into(), serde_json::json!(task.id))]
                .into_iter()
                .collect(),
        }];

        let job_range: Vec<_> = (0..jobs.len()).collect();

        let xs = get_target_hosts_by_fsname(&fsname, &context.pg_pool).await?;

        for x in xs {
            let path = match x.dev_path {
                Some(x) => x,
                None => continue,
            };

            let cfg = stratagem::StratagemConfig {
                flist_type: "none".into(),
                summarize_size: true,
                device: stratagem::StratagemDevice {
                    path,
                    groups: vec!["cloudsync".into()],
                },
                groups: vec![stratagem::StratagemGroup {
                    name: "filesync".into(),
                    rules: vec![stratagem::StratagemRule {
                        action: "LAT_SHELL_CMD_FID".into(),
                        expression: expression.clone(),
                        argument: "filesync".into(),
                        counter_name: Some("filesync".into()),
                    }],
                }],
            };

            jobs.push(SendJob {
                class_name: "ScanMdtJob".into(),
                args: vec![
                    ("fqdn".into(), serde_json::to_value(&x.fqdn)?),
                    ("uuid".into(), serde_json::to_value(&uuid)?),
                    ("fsname".into(), serde_json::to_value(&fsname)?),
                    ("config".into(), serde_json::to_value(cfg)?),
                    (
                        "depends_on_job_range".into(),
                        serde_json::to_value(&job_range)?,
                    ),
                ]
                .into_iter()
                .collect(),
            })
        }

        let kwargs: HashMap<String, String> =
            vec![("message".into(), "Stratagem: Cloudsync".into())]
                .into_iter()
                .collect();

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
    async fn run_fast_file_scan(
        context: &Context,
        fsname: String,
        report_duration: Option<GraphQLDuration>,
        purge_duration: Option<GraphQLDuration>,
    ) -> juniper::FieldResult<Command> {
        if let Some((r, p)) = report_duration.as_ref().zip(purge_duration.as_ref()) {
            if r.0 >= p.0 {
                return Err(FieldError::new(
                    "Report duration must be less than Purge duration.",
                    Value::null(),
                ));
            }
        }

        let uuid = Uuid::new_v4().to_hyphenated().to_string();

        let mut cleanup_tasks = vec![];

        let mut jobs = vec![SendJob {
            class_name: "ClearOldStratagemDataJob".into(),
            args: HashMap::<String, serde_json::Value>::new(),
        }];

        let mut groups = vec!["size_distribution".into(), "user_distribution".into()];

        let fs_id = fs_id_by_name(&context.pg_pool, &fsname).await?;

        if report_duration.is_some() {
            let task = insert_task(
                &format!("{}-warn_fids-fids_expiring_soon", uuid),
                &"created",
                false,
                false,
                &["stratagem.warning".into()],
                serde_json::json!({
                    "report_name": format!("expiring_fids-{}-{}.txt", fsname, uuid)
                }),
                fs_id,
                &context.pg_pool,
            )
            .await?;

            jobs.push(SendJob {
                class_name: "CreateTaskJob".into(),
                args: vec![("task_id".into(), serde_json::json!(task.id))]
                    .into_iter()
                    .collect(),
            });

            cleanup_tasks.push(task);

            groups.push("warn_fids".into());
        }

        if purge_duration.is_some() {
            let task = insert_task(
                &format!("{}-purge_fids-fids_expired", uuid),
                &"created",
                false,
                false,
                &["stratagem.purge".into()],
                serde_json::json!({}),
                fs_id,
                &context.pg_pool,
            )
            .await?;

            jobs.push(SendJob {
                class_name: "CreateTaskJob".into(),
                args: vec![("task_id".into(), serde_json::json!(task.id))]
                    .into_iter()
                    .collect(),
            });

            cleanup_tasks.push(task);

            groups.push("purge_fids".into());
        }

        let job_range: Vec<_> = (0..jobs.len()).collect();

        let xs = get_target_hosts_by_fsname(&fsname, &context.pg_pool).await?;

        for x in xs {
            let path = match x.dev_path {
                Some(x) => x,
                None => continue,
            };

            let mut cfg = stratagem::StratagemConfig {
                flist_type: "none".into(),
                summarize_size: true,
                device: stratagem::StratagemDevice {
                    path,
                    groups: groups.clone(),
                },
                groups: vec![
                    stratagem::StratagemGroup {
                        rules: vec![
                            stratagem::StratagemRule {
                                action: "LAT_COUNTER_INC".into(),
                                expression: "&& < size 1048576 != type S_IFDIR".into(),
                                argument: "SIZE < 1M".into(),
                                counter_name: None,
                            },
                            stratagem::StratagemRule {
                                action: "LAT_COUNTER_INC".into(),
                                expression: "&& >= size 1048576000000 != type S_IFDIR".into(),
                                argument: "SIZE >= 1T".into(),
                                counter_name: None,
                            },
                            stratagem::StratagemRule {
                                action: "LAT_COUNTER_INC".into(),
                                expression: "&& >= size 1048576000 != type S_IFDIR".into(),
                                argument: "SIZE >= 1G".into(),
                                counter_name: None,
                            },
                            stratagem::StratagemRule {
                                action: "LAT_COUNTER_INC".into(),
                                expression: "&& >= size 1048576 != type S_IFDIR".into(),
                                argument: "1M <= SIZE < 1G".into(),
                                counter_name: None,
                            },
                        ],
                        name: "size_distribution".into(),
                    },
                    stratagem::StratagemGroup {
                        rules: vec![stratagem::StratagemRule {
                            action: "LAT_ATTR_CLASSIFY".into(),
                            expression: "!= type S_IFDIR".into(),
                            argument: "uid".into(),
                            counter_name: Some("top_inode_users".into()),
                        }],
                        name: "user_distribution".into(),
                    },
                ],
            };

            if let Some(r) = report_duration.as_ref() {
                let expression = if let Some(p) = purge_duration.as_ref() {
                    format!(
                        "&& != type S_IFDIR && < atime - sys_time {} > atime - sys_time {}",
                        r.0.as_millis(),
                        p.0.as_millis()
                    )
                } else {
                    format!("&& != type S_IFDIR < atime - sys_time {}", r.0.as_millis())
                };

                cfg.groups.push(stratagem::StratagemGroup {
                    rules: vec![stratagem::StratagemRule {
                        action: "LAT_SHELL_CMD_FID".into(),
                        expression,
                        argument: "fids_expiring_soon".into(),
                        counter_name: Some("fids_expiring_soon".into()),
                    }],
                    name: "warn_fids".into(),
                });
            }

            if let Some(p) = purge_duration.as_ref() {
                cfg.groups.push(stratagem::StratagemGroup {
                    name: "purge_fids".into(),
                    rules: vec![stratagem::StratagemRule {
                        action: "LAT_SHELL_CMD_FID".into(),
                        expression: format!(
                            "&& != type S_IFDIR < atime - sys_time {}",
                            p.0.as_millis()
                        ),
                        argument: "fids_expired".into(),
                        counter_name: Some("fids_expired".into()),
                    }],
                });
            }

            jobs.push(SendJob {
                class_name: "FastFileScanMdtJob".into(),
                args: vec![
                    ("fqdn".into(), serde_json::to_value(&x.fqdn)?),
                    ("uuid".into(), serde_json::to_value(&uuid)?),
                    ("fsname".into(), serde_json::to_value(&fsname)?),
                    ("config".into(), serde_json::to_value(cfg)?),
                    (
                        "depends_on_job_range".into(),
                        serde_json::to_value(&job_range)?,
                    ),
                ]
                .into_iter()
                .collect(),
            })
        }

        let job_range: Vec<_> = (0..jobs.len()).collect();

        jobs.push(SendJob {
            class_name: "AggregateStratagemResultsJob",
            args: vec![
                ("fs_name".into(), serde_json::to_value(&fsname)?),
                (
                    "depends_on_job_range".into(),
                    serde_json::to_value(&job_range)?,
                ),
            ]
            .into_iter()
            .collect(),
        });

        for t in cleanup_tasks {
            jobs.push(SendJob {
                class_name: "RemoveTaskJob".into(),
                args: vec![
                    ("task_id".into(), serde_json::json!(t.id)),
                    (
                        "depends_on_job_range".into(),
                        serde_json::to_value(&job_range)?,
                    ),
                ]
                .into_iter()
                .collect(),
            })
        }

        let kwargs: HashMap<String, String> =
            vec![("message".into(), "Stratagem: Fast File Scan".into())]
                .into_iter()
                .collect();

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
    async fn run_stratagem(
        context: &Context,
        uuid: String,
        fsname: String,
        tasks: Vec<TaskArgs>,
        groups: Vec<stratagem::StratagemGroup>,
    ) -> juniper::FieldResult<Command> {
        let mut jobs: Vec<SendJob<HashMap<String, serde_json::Value>>> = vec![];

        let fs_id = fs_id_by_name(&context.pg_pool, &fsname).await?;

        let mut cleanup_tasks = vec![];

        for t in tasks {
            let args: HashMap<String, String> =
                t.pairs.into_iter().map(|x| (x.key, x.value)).collect();

            let task = insert_task(
                &t.name,
                "created",
                t.single_runner,
                t.keep_failed,
                &t.actions,
                serde_json::to_value(&args)?,
                fs_id,
                &context.pg_pool,
            )
            .await?;

            jobs.push(SendJob {
                class_name: "CreateTaskJob".into(),
                args: vec![("task_id".into(), serde_json::json!(task.id))]
                    .into_iter()
                    .collect(),
            });

            if t.needs_cleanup {
                cleanup_tasks.push(task)
            }
        }

        let job_range: Vec<_> = (0..jobs.len()).collect();

        let xs = get_target_hosts_by_fsname(&fsname, &context.pg_pool).await?;

        for t in xs {
            let path = match t.dev_path {
                Some(x) => x,
                None => continue,
            };

            let group_names: Vec<String> = groups.iter().map(|x| x.name.to_string()).collect();

            let cfg = stratagem::StratagemConfig {
                flist_type: "none".into(),
                summarize_size: true,
                groups: groups.clone(),
                device: stratagem::StratagemDevice {
                    path,
                    groups: group_names,
                },
            };

            jobs.push(SendJob {
                class_name: "ScanMdtJob".into(),
                args: vec![
                    ("fqdn".into(), serde_json::to_value(&t.fqdn)?),
                    ("uuid".into(), serde_json::to_value(&uuid)?),
                    ("fsname".into(), serde_json::to_value(&fsname)?),
                    ("config".into(), serde_json::to_value(cfg)?),
                    (
                        "depends_on_job_range".into(),
                        serde_json::to_value(&job_range)?,
                    ),
                ]
                .into_iter()
                .collect(),
            })
        }

        let job_range: Vec<_> = (0..jobs.len()).collect();

        for t in cleanup_tasks {
            jobs.push(SendJob {
                class_name: "RemoveTaskJob".into(),
                args: vec![
                    ("task_id".into(), serde_json::json!(t.id)),
                    (
                        "depends_on_job_range".into(),
                        serde_json::to_value(&job_range)?,
                    ),
                ]
                .into_iter()
                .collect(),
            })
        }

        let kwargs: HashMap<String, String> =
            vec![("message".into(), "Stratagem: Scanning all MDT's".into())]
                .into_iter()
                .collect();

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

    /// Delete a stratagem report
    #[graphql(arguments(filename(description = "The report filename to delete")))]
    async fn delete_stratagem_report(
        _context: &Context,
        filename: String,
    ) -> juniper::FieldResult<bool> {
        let report_base = get_report_path();
        let path = tokio::fs::canonicalize(report_base.join(filename)).await?;

        if !path.starts_with(report_base) {
            return Err(FieldError::new("Invalid path", Value::null()));
        }

        tokio::fs::remove_file(path).await?;

        Ok(true)
    }
    #[graphql(arguments(
        fsname(description = "Filesystem"),
        hotpool(description = "Name of Hot ostpool"),
        coldpool(description = "Name of Cold ostpool"),
        extendlayout(description = "Options to lfs mirror extend or hot -> cold files"),
        minage(description = "Minimum age of file before mirroring"),
        freehi(description = "Percent of free space when lpurge stops"),
        freelo(description = "Percent of free space when lpurge starts"),
    ))]
    /// Create Hotpool setups
    async fn create_hotpool(
        context: &Context,
        fsname: String,
        hotpool: String,
        coldpool: String,
        extendlayout: Option<String>,
        minage: i32,
        freehi: i32,
        freelo: i32,
    ) -> juniper::FieldResult<Command> {
        // Sanity check freehi and freelo
        if freehi > 99 || freehi <= 0 {
            return Err(FieldError::new(
                "Freehi out of range (0, 100)",
                Value::null(),
            ));
        }
        if freelo > 99 || freelo <= 0 {
            return Err(FieldError::new(
                "Freehi out of range (0, 100)",
                Value::null(),
            ));
        }
        if freehi < freelo {
            return Err(FieldError::new("Freehi less than freelo", Value::null()));
        }

        let fsid = sqlx::query!(
            r#"
                SELECT id FROM chroma_core_managedfilesystem WHERE name=$1 and not_deleted = 't'
            "#,
            fsname,
        )
        .fetch_optional(&context.pg_pool)
        .await?
        .map(|x| x.id)
        .ok_or_else(|| FieldError::new("Filesystem not found", Value::null()))?;

        let coldid = poolid(fsid, coldpool, &context.pg_pool)
            .await?
            .ok_or_else(|| FieldError::new("Cold OstPool not found", Value::null()))?;

        let hotid = poolid(fsid, hotpool, &context.pg_pool)
            .await?
            .ok_or_else(|| FieldError::new("Hot OstPool not found", Value::null()))?;

        let mut hp_data: HashMap<String, String> = vec![
            ("filesystem".into(), format!("{}", fsid)),
            ("hotpool".into(), format!("{}", hotid)),
            ("coldpool".into(), format!("{}", coldid)),
            ("minage".into(), format!("{}", minage)),
            ("freehi".into(), format!("{}", freehi)),
            ("freelo".into(), format!("{}", freelo)),
        ]
        .into_iter()
        .collect();

        if let Some(value) = extendlayout {
            hp_data.insert("extendlayout".into(), value);
        }

        let command_id: i32 = iml_job_scheduler_rpc::call(
            &context.rabbit_pool.get().await?,
            "create_hotpool",
            vec![hp_data],
            None,
        )
        .map_err(ImlApiError::ImlJobSchedulerRpcError)
        .await?;

        get_command(&context.pg_pool, command_id)
            .await
            .map_err(|e| e.into())
    }

    #[graphql(arguments(
        fsname(description = "Filesystem name"),
        state(description = "New state to transition to"),
    ))]
    async fn set_hotpool_state(
        context: &Context,
        fsname: String,
        state: HotpoolState,
    ) -> juniper::FieldResult<Command> {
        let hpid = hpid(fsname, &context.pg_pool).await?.ok_or_else(|| {
            FieldError::new(
                "Hotpool Configuration not found for filesystem",
                Value::null(),
            )
        })?;

        let obj = serde_json::json!([(
            (
                "chroma_core".to_string(),
                "hotpoolconfiguration".to_string()
            ),
            hpid,
            state.to_string()
        )]);
        let kwargs: HashMap<String, String> = vec![
            (
                "message".into(),
                format!("Setting Hotpool state to {}", &state),
            ),
            ("run".into(), "True".into()),
        ]
        .into_iter()
        .collect();

        let command_id: i32 = iml_job_scheduler_rpc::call(
            &context.rabbit_pool.get().await?,
            "set_state",
            vec![obj],
            Some(kwargs),
        )
        .map_err(ImlApiError::ImlJobSchedulerRpcError)
        .await?;

        get_command(&context.pg_pool, command_id)
            .await
            .map_err(|e| e.into())
    }
    #[graphql(arguments(fsname(description = "Filesystem"),))]
    async fn destroy_hotpool(context: &Context, fsname: String) -> juniper::FieldResult<Command> {
        let hpid = hpid(fsname, &context.pg_pool)
            .await?
            .ok_or_else(|| FieldError::new("Hotpool Configuration not found", Value::null()))?;

        let command_id: i32 = iml_job_scheduler_rpc::call(
            &context.rabbit_pool.get().await?,
            "remove_hotpool",
            vec![hpid],
            None,
        )
        .map_err(ImlApiError::ImlJobSchedulerRpcError)
        .await?;

        get_command(&context.pg_pool, command_id)
            .await
            .map_err(|e| e.into())
    }
}

async fn get_stratagem_files(
    (file_path, filename): (String, String),
) -> juniper::FieldResult<StratagemReport> {
    let attr = fs::metadata(file_path.to_string()).await?;

    Ok(StratagemReport {
        filename,
        modify_time: attr.modified()?.into(),
        size: attr.len() as i32,
    })
}

async fn hpid(fsname: String, pgpool: &PgPool) -> Result<Option<i32>, iml_postgres::sqlx::Error> {
    let xs = sqlx::query!(
        r#"
            SELECT hp.id AS id FROM chroma_core_hotpoolconfiguration hp
            INNER JOIN chroma_core_managedfilesystem fs ON hp.filesystem_id = fs.id
            WHERE hp.not_deleted = 't' AND fs.not_deleted = 't' AND fs.name=$1
        "#,
        fsname
    )
    .fetch_optional(pgpool)
    .await?
    .map(|x| x.id);

    Ok(xs)
}

async fn poolid(
    fsid: i32,
    poolname: String,
    pgpool: &PgPool,
) -> Result<Option<i32>, iml_postgres::sqlx::Error> {
    let rc = sqlx::query!(
        r#"
            SELECT id FROM chroma_core_ostpool WHERE filesystem_id=$1 AND name=$2 AND not_deleted = 't'
        "#,
        fsid,
        poolname,
    )
    .fetch_optional(pgpool)
    .await?
        .map(|x| x.id);
    Ok(rc)
}

#[derive(Debug)]
struct TargetHost {
    name: String,
    dev_path: Option<String>,
    fqdn: String,
}

async fn get_target_hosts_by_fsname(
    fsname: &str,
    pg_pool: &PgPool,
) -> Result<Vec<TargetHost>, ImlApiError> {
    let xs = sqlx::query_as!(
        TargetHost,
        r#"
            SELECT t.name, t.dev_path, h.fqdn
            FROM target t
            INNER JOIN chroma_core_managedhost h
            ON t.active_host_id = h.id
            WHERE $1 = ANY(t.filesystems)
            AND h.not_deleted = 't'
        "#,
        fsname
    )
    .fetch(pg_pool)
    .try_filter(|x| {
        let is_mdt = (&x.name)
            .rsplitn(2, '-')
            .nth(0)
            .filter(|x| x.starts_with("MDT"))
            .is_some();

        future::ready(is_mdt)
    })
    .try_collect()
    .await?;

    tracing::debug!("Target hosts for {}: {:?}", fsname, xs);

    Ok(xs)
}
