// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::{
    action_runner::invoke,
    command_plan::{
        command_plan_writer, Change, CommandJobWriter, CommandJobWriterExt as _,
        CommandPlanWriterExt as _, CommandStepWriterExt as _, JobGraph, JobGraphs, OutputWriter,
    },
    state_schema::Input,
    Error,
};
use emf_postgres::PgPool;
use emf_tracing::tracing;
use emf_wire_types::State;
use futures::{
    future::{join_all, Shared},
    Future, FutureExt, StreamExt,
};
use petgraph::{graph::NodeIndex, visit::Dfs, Direction};
use std::{cmp::max, collections::HashMap, ops::Deref, pin::Pin, sync::Arc};
use tokio::sync::mpsc::{self, UnboundedSender};
use tokio_stream::wrappers::UnboundedReceiverStream;

pub fn get_executor(pg_pool: &PgPool) -> UnboundedSender<(i32, JobGraphs, Vec<NodeIndex>)> {
    let (tx, rx) = mpsc::unbounded_channel();
    let mut rx = UnboundedReceiverStream::new(rx);

    let pg_pool = pg_pool.clone();

    tokio::spawn(async move {
        while let Some((plan_id, job_graphs, sorted_jobs)) = rx.next().await {
            let tx = match command_plan_writer(&pg_pool, plan_id, &job_graphs).await {
                Ok(tx) => tx,
                Err(e) => {
                    tracing::warn!("Could not create CommandPlanWriter, skipping: {:?}", e);
                    continue;
                }
            };

            let mut visited: HashMap<
                NodeIndex,
                Shared<Pin<Box<dyn Future<Output = State> + std::marker::Send>>>,
            > = HashMap::new();

            let mut stacks = vec![];

            for jobs_idx in sorted_jobs {
                let xs: Vec<_> = visited
                    .iter()
                    .filter(|(visited, _)| job_graphs.find_edge(**visited, jobs_idx).is_some())
                    .map(|(_, f)| f.clone())
                    .collect();

                let tx = tx.get_command_job_writer(jobs_idx);

                let (name, job_graph) = &job_graphs[jobs_idx];
                let name = name.to_string();
                let name2 = name.to_string();
                let job_graph2 = Arc::clone(job_graph);

                tracing::debug!("Found Job: {}", name);

                let pg_pool = pg_pool.clone();

                let fut = async move {
                    tracing::info!("Starting Job: {}", name);

                    let state = join_all(xs).await.into_iter().fold(State::Completed, max);

                    if state == State::Canceled || state == State::Failed {
                        tracing::info!("Job {} canceled because parent job {}", name, state);

                        return State::Canceled;
                    }

                    let stacks = build_execution_graph(&pg_pool, tx, job_graph2, invoke_box);

                    let mut hndls = vec![];

                    for stack in stacks {
                        let join = tokio::spawn(stack);

                        hndls.push(join);
                    }

                    join_all(hndls)
                        .await
                        .into_iter()
                        .map(|x| match x {
                            Ok(x) => x,
                            Err(_) => State::Failed,
                        })
                        .fold(State::Completed, max)
                }
                .boxed()
                .shared();

                visited.insert(jobs_idx, fut.clone());

                if job_graphs
                    .edges_directed(jobs_idx, Direction::Outgoing)
                    .next()
                    .is_none()
                {
                    tracing::debug!("Pushing Job {} fut", name2);
                    stacks.push(fut);
                }
            }

            tracing::debug!("Number of job stacks: {}", stacks.len());

            for stack in stacks {
                tokio::spawn(stack);
            }
        }
    });

    tx
}

fn invoke_box(
    pg_pool: PgPool,
    stdout_writer: OutputWriter,
    stderr_writer: OutputWriter,
    input: &Input,
) -> Pin<Box<dyn Future<Output = Result<(), Error>> + Send + '_>> {
    Box::pin(invoke(pg_pool, stdout_writer, stderr_writer, input))
}

type InvokeBoxFn = fn(
    pg_pool: PgPool,
    OutputWriter,
    OutputWriter,
    &Input,
) -> Pin<Box<dyn Future<Output = Result<(), Error>> + Send + '_>>;

pub(crate) fn build_execution_graph(
    pool: &PgPool,
    tx: CommandJobWriter,
    g: Arc<JobGraph>,
    invoke_fn: InvokeBoxFn,
) -> Vec<Shared<Pin<Box<dyn Future<Output = State> + std::marker::Send>>>> {
    let mut visited: HashMap<
        NodeIndex<u32>,
        Shared<Pin<Box<dyn Future<Output = State> + std::marker::Send>>>,
    > = HashMap::new();

    let mut dfs = Dfs::new(g.deref(), NodeIndex::new(0));

    let mut stacks = vec![];

    while let Some(curr) = dfs.next(g.deref()) {
        let xs: Vec<_> = visited
            .iter()
            .filter(|(visited, _)| g.find_edge(**visited, curr).is_some())
            .map(|(_, f)| f.clone())
            .collect();

        let g2 = Arc::clone(&g);

        let tx = tx.get_command_state_writer(curr);

        let pool = pool.clone();

        let fut = async move {
            let step = &g2[curr];
            let inputs = &step.inputs;
            let state = join_all(xs).await.into_iter().fold(State::Completed, max);

            tx.send_change(Change::Started(chrono::Utc::now()));

            if state == State::Canceled || state == State::Failed {
                let msg = format!("{} canceled because parent {}", step, state);

                tracing::info!("{}", msg);

                tx.send_change(Change::State(State::Canceled));
                tx.send_change(Change::Ended(chrono::Utc::now()));
                tx.send_change(Change::Result(Err(msg)));

                return State::Canceled;
            }

            tracing::info!("Running: {}", step);

            tx.send_change(Change::State(State::Running));

            let (stdout, stderr) = tx.get_output_handles();

            let r = invoke_fn(pool, stdout, stderr, inputs).await;

            let state = match r {
                Ok(_) => {
                    tracing::info!("{} Completed", step);

                    State::Completed
                }
                Err(e) => {
                    tracing::info!("{} failed: {:?}", step, e);

                    tx.send_change(Change::Result(Err(format!("{}", e))));
                    State::Failed
                }
            };

            tx.send_change(Change::State(state));
            tx.send_change(Change::Ended(chrono::Utc::now()));

            state
        }
        .boxed()
        .shared();

        visited.insert(curr, fut.clone());

        if g.edges_directed(curr, Direction::Outgoing).next().is_none() {
            stacks.push(fut);
        }
    }

    stacks
}
