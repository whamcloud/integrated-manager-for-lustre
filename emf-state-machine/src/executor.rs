// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::{action_runner::invoke, command_plan::JobGraph, state_schema::Input, Error};
use emf_tracing::tracing;
use futures::{
    future::{join_all, Shared},
    Future, FutureExt, StreamExt,
};
use petgraph::{graph::NodeIndex, visit::Dfs, Direction};
use std::{cmp::max, collections::HashMap, fmt, ops::Deref, pin::Pin, sync::Arc};
use tokio::sync::mpsc::{self, UnboundedSender};
use tokio_stream::wrappers::UnboundedReceiverStream;

pub fn get_executor() -> UnboundedSender<HashMap<String, JobGraph>> {
    let (tx, rx) = mpsc::unbounded_channel();
    let mut rx = UnboundedReceiverStream::new(rx);

    tokio::spawn(async move {
        while let Some(job_graphs) = rx.next().await {
            for (n, g) in job_graphs {
                tokio::spawn(execute_graph(Arc::new(g)));
            }
        }
    });

    tx
}

fn invoke_box(input: &Input) -> Pin<Box<dyn Future<Output = Result<(), Error>> + Send + '_>> {
    Box::pin(invoke(input))
}

async fn execute_graph(g: Arc<JobGraph>) {
    let stacks = build_execution_graph(Arc::clone(&g), invoke_box);

    for stack in stacks {
        tokio::spawn(stack);
    }
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Ord, PartialOrd)]
pub(crate) enum State {
    Pending,
    Completed,
    Failed,
    Canceled,
}

impl fmt::Display for State {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x = match self {
            Self::Pending => "pending",
            Self::Completed => "completed",
            Self::Canceled => "canceled",
            Self::Failed => "failed",
        };

        write!(f, "{}", x)
    }
}

pub(crate) fn build_execution_graph(
    g: Arc<JobGraph>,
    invoke_fn: fn(&Input) -> Pin<Box<dyn Future<Output = Result<(), Error>> + Send + '_>>,
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

        let fut = async move {
            let step = &g2[curr];
            let inputs = &step.inputs;
            let state = join_all(xs).await.into_iter().fold(State::Completed, max);

            if state == State::Canceled || state == State::Failed {
                tracing::info!("{} canceled because parent {}", step, state);

                return State::Canceled;
            }

            tracing::info!("Running: {}", step);

            let r = invoke_fn(inputs).await;

            if r.is_ok() {
                tracing::info!("{} Completed", step);

                State::Completed
            } else {
                tracing::info!("{} failed: {:?}", step, r);

                State::Failed
            }
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
