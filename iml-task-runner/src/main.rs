// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future::try_join_all, lock::Mutex, TryFutureExt};
use iml_action_client::invoke_rust_agent;
use iml_orm::{
    clientmount::ChromaCoreLustreclientmount as Client,
    filesystem::ChromaCoreManagedfilesystem as Filesystem,
    hosts::ChromaCoreManagedhost as Host,
    task::{self, ChromaCoreTask as Task},
    tokio_diesel::{AsyncRunQueryDsl as _, OptionalExtension as _},
    DbPool,
};
use iml_postgres::{
    get_db_pool,
    sqlx::{self, prelude::Executor, PgPool},
};
use iml_tracing::tracing;
use iml_wire_types::{
    db::{FidTaskQueue, LustreFid},
    AgentResult, FidError, FidItem, TaskAction,
};
use std::{
    collections::{HashMap, HashSet},
    str::FromStr,
    sync::Arc,
    time::Duration,
};
use tokio::time;

pub mod error;

// Number of fids to chunk together
const FID_LIMIT: i64 = 2000;
// Number of seconds between cycles
const DELAY: u64 = 5;

async fn available_workers(
    pool: &DbPool,
    active: Arc<Mutex<HashSet<i32>>>,
) -> Result<Vec<Client>, error::ImlTaskRunnerError> {
    let list = active.lock().await;
    let clients: Vec<Client> = Client::available(list.iter().copied())
        .get_results_async(pool)
        .await?;
    Ok(clients)
}

async fn tasks_per_worker(
    pool: &DbPool,
    worker: &Client,
) -> Result<Vec<Task>, error::ImlTaskRunnerError> {
    let fs_id = {
        let fsmap: Option<Filesystem> = Filesystem::by_name(&worker.filesystem)
            .first_async(pool)
            .await
            .optional()?;
        match fsmap {
            Some(f) => f.id,
            None => return Ok(vec![]),
        }
    };

    let tasks: Vec<Task> = Task::outgestable(fs_id, worker.host_id)
        .get_results_async(pool)
        .await?;
    Ok(tasks)
}

async fn worker_fqdn(pool: &DbPool, worker: &Client) -> Result<String, error::ImlTaskRunnerError> {
    let host: Host = Host::by_id(worker.host_id).first_async(pool).await?;
    Ok(host.fqdn)
}

async fn send_work(
    orm_pool: &DbPool,
    pg_pool: &PgPool,
    fqdn: &str,
    fsname: &str,
    task: &Task,
    host_id: i32,
) -> Result<i64, error::ImlTaskRunnerError> {
    let taskargs: HashMap<String, String> = serde_json::from_value(task.args.clone())?;

    // Setup running_on if unset
    if task.single_runner && task.running_on_id.is_none() {
        tracing::debug!(
            "Attempting to Set Task {} ({}) running_on to host {} ({})",
            task.name,
            task.id,
            fqdn,
            host_id
        );
        let rc = task::set_running_on(task.id, host_id)
            .execute_async(orm_pool)
            .await?;
        if rc == 1 {
            tracing::info!(
                "Set Task {} ({}) running on host {} ({})",
                task.name,
                task.id,
                fqdn,
                host_id
            );
        } else {
            tracing::debug!(
                "Failed to Set Task {} running_on to host {}: {}",
                task.name,
                fqdn,
                rc
            );
            return Ok(0);
        }
    }

    tracing::debug!("send_work({}, {}, {})", fqdn, fsname, task.name);

    let mut trans = pg_pool.begin().await?;

    let rowlist = sqlx::query_as!(
        FidTaskQueue,
        r#"
        DELETE FROM chroma_core_fidtaskqueue 
        WHERE id in ( 
            SELECT id FROM chroma_core_fidtaskqueue WHERE task_id = $1 LIMIT $2 FOR UPDATE SKIP LOCKED 
        ) RETURNING id, fid as "fid: _", data, task_id"#,
        task.id, FID_LIMIT,
    )
        .fetch_all(&mut trans)
        .await?;

    tracing::debug!(
        "send_work({}, {}, {}) found {} fids",
        fqdn,
        fsname,
        task.name,
        rowlist.len()
    );

    if rowlist.is_empty() {
        return trans.commit().map_ok(|_| 0).err_into().await;
    }

    let fidlist: Vec<FidItem> = rowlist
        .into_iter()
        .map(|row| {
            let ft: FidTaskQueue = row.into();
            FidItem {
                fid: ft.fid.to_string(),
                data: ft.data,
            }
        })
        .collect();

    let completed = fidlist.len();
    let mut failed = 0;
    let args = TaskAction(fsname.to_string(), taskargs, fidlist);

    // send fids to actions runner
    // action names on Agents are "action.ACTION_NAME"
    for action in task.actions.iter().map(|a| format!("action.{}", a)) {
        match invoke_rust_agent(fqdn, &action, &args).await {
            Err(e) => {
                tracing::info!("Failed to send {} to {}: {:?}", &action, fqdn, e);
                return trans.rollback().map_ok(|_| 0).err_into().await;
            }
            Ok(res) => {
                let agent_result: AgentResult = serde_json::from_value(res)?;
                match agent_result {
                    Ok(data) => {
                        tracing::debug!("Success {} on {}: {:?}", &action, fqdn, data);
                        let errors: Vec<FidError> = serde_json::from_value(data)?;
                        failed += errors.len();

                        if task.keep_failed {
                            let task_id = task.id;
                            for err in errors.iter() {
                                let fid = LustreFid::from_str(&err.fid)
                                    .expect("FIXME: This needs proper error handling");

                                // #FIXME: This would be better as a bulk insert
                                if let Err(e) = trans
                                    .execute(
                                        sqlx::query!(
                                            r#"
                                                INSERT INTO chroma_core_fidtaskerror (fid, task_id, data, errno)
                                                VALUES ($1, $2, $3, $4)"#,
                                            fid as LustreFid,
                                            task_id,
                                            err.data,
                                            err.errno
                                        )
                                    )
                                    .await
                                {
                                    tracing::info!(
                                        "Failed to insert fid error ({} : {}): {}",
                                        err.fid,
                                        err.errno,
                                        e
                                    );
                                }
                            }
                        }
                    }
                    Err(err) => {
                        tracing::info!("Failed {} on {}: {}", &action, fqdn, err);
                        return trans.rollback().map_ok(|_| 0).err_into().await;
                    }
                }
            }
        }
    }

    trans.commit().await?;

    if completed > 0 || failed > 0 {
        task::increase_finished(task.id, completed as i64, failed as i64)
            .execute_async(orm_pool)
            .await?;
    }

    Ok(completed as i64)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let orm_pool = iml_orm::pool()?;
    let pg_pool = get_db_pool(5).await?;
    let activeclients = Arc::new(Mutex::new(HashSet::new()));

    // Task Runner Loop
    let mut interval = time::interval(Duration::from_secs(DELAY));
    loop {
        interval.tick().await;

        let workers = available_workers(&orm_pool, activeclients.clone())
            .await
            .unwrap_or_default();

        activeclients
            .lock()
            .await
            .extend(workers.iter().map(|w| w.id));

        tokio::spawn({
            let pg_pool = pg_pool.clone();
            try_join_all(workers.into_iter().map(|worker| {
                let pg_pool = pg_pool.clone();
                let fsname = worker.filesystem.clone();
                let orm_pool = orm_pool.clone();
                let activeclients = activeclients.clone();

                async move {
                    let tasks = tasks_per_worker(&orm_pool, &worker).await?;
                    let fqdn = worker_fqdn(&orm_pool, &worker).await?;
                    let host_id = worker.host_id;

                    let rc =
                        try_join_all(tasks.into_iter().map(|task| {
                            let pg_pool = pg_pool.clone();
                            let orm_pool = orm_pool.clone();
                            let fsname = fsname.clone();
                            let fqdn = fqdn.clone();
                            async move {
                                let mut count = 0;
                                loop {
                                    let rc = send_work(
                                        &orm_pool, &pg_pool, &fqdn, &fsname, &task, host_id,
                                    )
                                    .await
                                    .map_err(|e| {
                                        tracing::warn!("send_work({}) failed {:?}", task.name, e);
                                        e
                                    })?;
                                    count += 1;
                                    if rc < FID_LIMIT || count > 10 {
                                        break;
                                    }
                                }
                                Ok::<_, error::ImlTaskRunnerError>(())
                            }
                        }))
                        .await;

                    activeclients.lock().await.remove(&worker.id);
                    rc
                }
            }))
        });
    }
}
