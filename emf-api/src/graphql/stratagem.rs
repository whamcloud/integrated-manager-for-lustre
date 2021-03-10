// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    error::EmfApiError,
    graphql::{fs_id_by_name, insert_fidlist, insert_task, Context, SendJob},
};
use emf_manager_env::get_report_path;
use emf_wire_types::{
    duration::GraphQLDuration, stratagem, task::TaskArgs, Command, StratagemConfiguration,
    StratagemConfigurationOutput, StratagemReport,
};
use futures::{
    future::{self, try_join_all},
    TryFutureExt, TryStreamExt,
};
use juniper::{FieldError, Value};
use sqlx::postgres::PgPool;
use std::collections::HashMap;
use tokio::fs;
use tokio_stream::wrappers::ReadDirStream;
use uuid::Uuid;

pub(crate) struct StratagemQuery;

#[juniper::graphql_object(Context = Context)]
impl StratagemQuery {
    /// List all stratagem configurations
    async fn stratagem_configurations(
        context: &Context,
        fs_id: Option<i32>,
    ) -> juniper::FieldResult<Vec<StratagemConfigurationOutput>> {
        let xs = sqlx::query_as!(
            StratagemConfiguration,
            r#"
            SELECT * from stratagemconfiguration
            WHERE ($1::int IS NULL OR filesystem_id = $1)
        "#,
            fs_id
        )
        .fetch(&context.pg_pool)
        .map_ok(|x| x.into())
        .try_collect()
        .await?;

        Ok(xs)
    }
    /// List completed Stratagem reports that currently reside on the manager node.
    /// Note: All report names must be valid unicode.
    async fn stratagem_reports(_context: &Context) -> juniper::FieldResult<Vec<StratagemReport>> {
        let paths = tokio::fs::read_dir(get_report_path())
            .map_ok(ReadDirStream::new)
            .await?;

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
    async fn run_task_fidlist(
        context: &Context,
        jobname: String,
        taskname: String,
        fsname: String,
        arguments: String,
        fidlist: Vec<String>,
    ) -> juniper::FieldResult<bool> {
        let uuid = Uuid::new_v4().to_hyphenated().to_string();

        let fs_id = fs_id_by_name(&context.pg_pool, &fsname).await?;
        let taskname = format!("stratagem.{}", taskname);

        let a = serde_json::from_str(&arguments)?;
        let task = insert_task(
            &format!("{}-{}", uuid, jobname),
            "created",
            false,
            false,
            &vec![taskname.into()],
            serde_json::from_value(a)?,
            fs_id,
            &context.pg_pool,
        )
        .await?;

        insert_fidlist(fidlist, task.id, &context.pg_pool).await?;
        Ok(true)
    }
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
            &["stratagem.filesync".into()],
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
            class_name: "CreateTaskJob",
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
                class_name: "ScanMdtJob",
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

        todo!();
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
            &["stratagem.cloudsync".into()],
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
            class_name: "CreateTaskJob",
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
                    name: "cloudsync".into(),
                    rules: vec![stratagem::StratagemRule {
                        action: "LAT_SHELL_CMD_FID".into(),
                        expression: expression.clone(),
                        argument: "cloudsync".into(),
                        counter_name: Some("cloudsync".into()),
                    }],
                }],
            };

            jobs.push(SendJob {
                class_name: "ScanMdtJob",
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

        todo!();
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
            class_name: "ClearOldStratagemDataJob",
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
                class_name: "CreateTaskJob",
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
                class_name: "CreateTaskJob",
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
                class_name: "FastFileScanMdtJob",
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
                class_name: "RemoveTaskJob",
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

        todo!();
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
                class_name: "CreateTaskJob",
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
                class_name: "ScanMdtJob",
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
                class_name: "RemoveTaskJob",
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

        todo!();
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

#[derive(Debug)]
struct TargetHost {
    name: String,
    dev_path: Option<String>,
    fqdn: String,
}

async fn get_target_hosts_by_fsname(
    fsname: &str,
    pg_pool: &PgPool,
) -> Result<Vec<TargetHost>, EmfApiError> {
    let xs = sqlx::query_as!(
        TargetHost,
        r#"
            SELECT t.name as "name!", t.dev_path, h.fqdn as "fqdn!"
            FROM target t
            INNER JOIN host h
            ON t.active_host_id = h.id
            WHERE $1 = ANY(t.filesystems)
        "#,
        fsname
    )
    .fetch(pg_pool)
    .try_filter(|x| {
        let is_mdt = (&x.name)
            .rsplitn(2, '-')
            .next()
            .filter(|x| x.starts_with("MDT"))
            .is_some();

        future::ready(is_mdt)
    })
    .try_collect()
    .await?;

    tracing::debug!("Target hosts for {}: {:?}", fsname, xs);

    Ok(xs)
}
