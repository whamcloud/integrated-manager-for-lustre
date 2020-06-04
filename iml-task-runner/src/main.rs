// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future::try_join_all, lock::Mutex, TryFutureExt};
use iml_action_client::invoke_rust_agent;
use iml_orm::{
    clientmount::ChromaCoreLustreclientmount as Client,
    filesystem::ChromaCoreManagedfilesystem as Filesystem,
    hosts::ChromaCoreManagedhost as Host,
    task::ChromaCoreTask as Task,
    tokio_diesel::{AsyncRunQueryDsl as _, OptionalExtension as _},
    DbPool,
};
use iml_postgres::SharedClient;
use iml_wire_types::{db::FidTaskQueue, FidItem, TaskAction};
use std::{
    collections::{HashMap, HashSet},
    sync::Arc,
    time::Duration,
};
use tokio::time;

pub mod error;

// Number of fids to chunk together
const FID_LIMIT: u32 = 2000;
// Number of seconds between cycles
const DELAY: u64 = 5;

async fn available_workers(
    pool: &DbPool,
    active: Arc<Mutex<HashSet<i32>>>,
) -> Result<Vec<Client>, error::ImlTaskRunnerError> {
    let list = active.lock().await;
    let clients: Vec<Client> = Client::not_ids(list.iter().copied())
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
    let host: Host = Host::by_id(worker.host_id)
        .first_async(pool)
        .await?;
    Ok(host.fqdn)
}

async fn send_work(
    shared_client: SharedClient,
    fqdn: String,
    fsname: String,
    task: &Task,
) -> Result<(), error::ImlTaskRunnerError> {
    let taskargs: HashMap<String, String> = serde_json::from_value(task.args.clone())?;

    tracing::debug!("send_work({}, {}, {})", &fqdn, &fsname, task.name);

    let mut c = shared_client.lock().await;
    let trans = c.transaction().await?;
    let sql = "DELETE FROM chroma_core_fidtaskqueue WHERE id in ( SELECT id FROM chroma_core_fidtaskqueue WHERE task_id = $1 LIMIT $2 SKIP LOCKED ) RETURNING *";
    let s = trans.prepare(sql).await?;
    let rowlist = trans.query(&s, &[&task.id, &FID_LIMIT]).await?;

    let fidlist = rowlist.into_iter().map(|row| {
        let ft: FidTaskQueue = row.into();
        FidItem {
            fid: ft.fid.to_string(),
            data: ft.data
        }
    }).collect();

    let args = TaskAction(fsname, taskargs, fidlist);

    // send fids to actions runner
    for action in task.actions.iter() {
        let (_, fut) = invoke_rust_agent(&fqdn, action, &args);
        match fut.await {
            Err(e) => {
                tracing::info!("Failed to send {} to {}: {}", &action, &fqdn, e);
                trans.rollback().await?;
                return Ok(());
            }
            Ok(_res) => {
                tracing::debug!("Success {} on {}", &action, &fqdn);
                // @@ check for failed fids and move them to fidtaskerror
            }
        }
    }

    trans.commit().err_into().await
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let (db_client, _conn) = iml_postgres::connect().await?;
    let shared_client = iml_postgres::shared_client(db_client);
    let pool = iml_orm::pool()?;
    let activeclients = Arc::new(Mutex::new(HashSet::new()));

    // Task Runner Loop
    let mut interval = time::interval(Duration::from_secs(DELAY));
    loop {
        interval.tick().await;

        let workers = available_workers(&pool, activeclients.clone()).await.unwrap_or(vec![]);

        tokio::spawn({
            let shared_client = shared_client.clone();
            try_join_all(workers.into_iter().map(|worker| { 
                let shared_client = shared_client.clone();
                let fsname = worker.filesystem.clone();
                let pool = pool.clone();
                let activeclients = activeclients.clone();

                async move {
                    activeclients.lock().await.insert(worker.id);
                    let tasks = tasks_per_worker(&pool, &worker).await?;
                    let fqdn = worker_fqdn(&pool, &worker).await?;
                    

                    let rc = try_join_all(tasks.into_iter().map(|task| {
                        let shared_client = shared_client.clone();
                        let fsname = fsname.clone();
                        let fqdn = fqdn.clone();
                        async move {
                            send_work(shared_client.clone(), fqdn, fsname, &task).await
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
