// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{job::Job, step::Steps, Error};
use future::Aborted;
use futures::future::{self, abortable};
use futures::{future::AbortHandle, lock::Mutex};
use iml_action_client::Client;
use iml_postgres::{sqlx, PgPool};
use iml_tracing::tracing;
use iml_wire_types::{
    state_machine,
    state_machine::{Command, CommandRecord, CurrentState},
};
use std::{collections::HashMap, sync::Arc, time::Duration};
use tokio::time;
use uuid::Uuid;

/*
1. Create command
2. Create jobs
3. Add jobs to command
3. push jobs into job_queue
4. Run each job in separate task, accounting for any dependendent jobs that came before.
*/

pub enum JobState {
    Pending,
    Running(Option<AbortHandle>),
}

impl JobState {
    fn is_pending(&self) -> bool {
        match self {
            Self::Pending => true,
            Self::Running(_) => false,
        }
    }
    fn is_running(&self) -> bool {
        !self.is_pending()
    }
}

pub type JobStates = Arc<Mutex<HashMap<i32, (state_machine::Job, JobState)>>>;

pub async fn run_command(
    pool: &PgPool,
    job_states: &JobStates,
    cmd: Command,
) -> Result<CommandRecord, Error> {
    let mut transaction = pool.begin().await?;

    let x = sqlx::query_as!(
        CommandRecord,
        r#"
        INSERT INTO command (message)
        VALUES ($1)
        RETURNING id, start_time, end_time, state as "state: CurrentState", message, jobs
    "#,
        cmd.message
    )
    .fetch_one(&mut transaction)
    .await?;

    let mut jobs = vec![];

    for job in cmd.jobs {
        let locks = job.get_locks(&pool).await?;
        let locks = locks
            .into_iter()
            .map(|x| serde_json::to_value(x))
            .collect::<Result<Vec<_>, _>>()?;

        let job_id = sqlx::query!(
            r#"
            INSERT INTO job (command_id, job, wait_for_jobs, locked_records)
            VALUES ($1, $2, array[]::int[], $3)
            RETURNING id
        "#,
            x.id,
            serde_json::to_value(&job)?,
            &locks
        )
        .fetch_one(&mut transaction)
        .await?
        .id;

        jobs.push((job_id, (job, JobState::Pending)));
    }

    let ids: Vec<i32> = jobs.iter().map(|x| x.0).collect();

    sqlx::query!("UPDATE command SET jobs = $1", &ids)
        .execute(&mut transaction)
        .await?;

    job_states.lock().await.extend(jobs);

    transaction.commit().await?;

    Ok(x)
}

pub async fn run_jobs(client: Client, pool: PgPool, job_states: JobStates) {
    loop {
        let job_states = Arc::clone(&job_states);

        let xs: HashMap<i32, Steps> = {
            let mut x = job_states.lock().await;

            x.iter_mut()
                .filter_map(|(k, (job, state))| {
                    if state.is_pending() {
                        Some((*k, job.get_steps()))
                    } else {
                        None
                    }
                })
                .collect()
        };

        for (k, steps) in xs {
            let client = client.clone();
            let job_states = Arc::clone(&job_states);
            let pool = pool.clone();

            tokio::spawn(async move {
                let r = run_steps(client, pool.clone(), k, steps, Arc::clone(&job_states)).await;

                let mut lock = job_states.lock().await;

                lock.remove(&k);

                let end_state = match r {
                    Ok(_) => state_machine::CurrentState::Succeeded,
                    Err(Error::Aborted(_)) => state_machine::CurrentState::Cancelled,
                    Err(e) => state_machine::CurrentState::Failed,
                };

                sqlx::query!(
                    r#"
                    UPDATE job
                    SET
                        state = $1,
                        end_time = now()
                "#,
                    end_state as state_machine::CurrentState
                )
                .execute(&pool)
                .await;
            });
        }

        time::sleep(Duration::from_secs(1)).await
    }
}

async fn run_steps(
    client: Client,
    pool: PgPool,
    job_id: i32,
    steps: Steps,
    job_states: JobStates,
) -> Result<(), Error> {
    for (f, args) in steps.0 {
        let fut = f(pool.clone(), args);
        let (fqdn, action, args) = fut.await?;

        let uuid = Uuid::new_v4();

        let fut = client.invoke_rust_agent_expect_result(fqdn.to_string(), action, args, &uuid);
        let (fut, h) = abortable(fut);

        {
            let mut lock = job_states.lock().await;

            let (job, _) = lock.remove(&job_id).unwrap();

            lock.insert(job_id, (job, JobState::Running(Some(h))));
        }

        match fut.await {
            Err(Aborted) => {
                let r = client.cancel_request(fqdn, &uuid).await;

                return Err(Error::Aborted(Aborted));
            }
            Ok(Err(e)) => {
                tracing::error!("Step failed: {:?}", e);

                return Err(e.into());
            }
            Ok(Ok(x)) => tracing::info!("Got {:?}", x),
        };
    }

    Ok(())
}
