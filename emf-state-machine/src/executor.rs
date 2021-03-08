// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::{
    action_runner::invoke,
    command_plan::{
        command_plan_writer, Change, CommandPlanWriter, CommandPlanWriterExt as _,
        CommandStepWriterExt as _, JobGraph, OutputWriter,
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

pub fn get_executor(pg_pool: &PgPool) -> UnboundedSender<(i32, HashMap<String, JobGraph>)> {
    let (tx, rx) = mpsc::unbounded_channel();
    let mut rx = UnboundedReceiverStream::new(rx);

    let pg_pool = pg_pool.clone();

    tokio::spawn(async move {
        while let Some((plan_id, job_graphs)) = rx.next().await {
            let tx = match command_plan_writer(&pg_pool, plan_id, &job_graphs).await {
                Ok(tx) => tx,
                Err(e) => {
                    tracing::warn!("Could not create CommandPlanWriter, skipping: {:?}", e);
                    continue;
                }
            };

            for (n, g) in job_graphs {
                tokio::spawn(execute_graph(n, Arc::new(g), tx.clone()));
            }
        }
    });

    tx
}

fn invoke_box(
    stdout_writer: OutputWriter,
    stderr_writer: OutputWriter,
    input: &Input,
) -> Pin<Box<dyn Future<Output = Result<(), Error>> + Send + '_>> {
    Box::pin(invoke(stdout_writer, stderr_writer, input))
}

async fn execute_graph(job_name: String, g: Arc<JobGraph>, tx: CommandPlanWriter) {
    let stacks = build_execution_graph(&job_name, tx, Arc::clone(&g), invoke_box);

    for stack in stacks {
        tokio::spawn(stack);
    }
}

pub(crate) fn build_execution_graph(
    job_name: &str,
    tx: CommandPlanWriter,
    g: Arc<JobGraph>,
    invoke_fn: fn(
        OutputWriter,
        OutputWriter,
        &Input,
    ) -> Pin<Box<dyn Future<Output = Result<(), Error>> + Send + '_>>,
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

        let tx = tx.get_command_state_writer(job_name, curr);

        let fut = async move {
            let step = &g2[curr];
            let inputs = &step.inputs;
            let state = join_all(xs).await.into_iter().fold(State::Completed, max);

            tx.send(Change::Started(chrono::Utc::now()));

            if state == State::Canceled || state == State::Failed {
                tracing::info!("{} canceled because parent {}", step, state);

                tx.send(Change::State(State::Canceled));
                tx.send(Change::Ended(chrono::Utc::now()));

                return State::Canceled;
            }

            tracing::info!("Running: {}", step);

            let (stdout, stderr) = tx.get_output_handles();

            let r = invoke_fn(stdout, stderr, inputs).await;

            let state = if r.is_ok() {
                tracing::info!("{} Completed", step);

                State::Completed
            } else {
                tracing::info!("{} failed: {:?}", step, r);

                State::Failed
            };

            tx.send(Change::State(state));
            tx.send(Change::Ended(chrono::Utc::now()));

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
