// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::Error;
use bytes::Bytes;
use chrono::{DateTime, Utc};
use emf_lib_state_machine::input_document::{InputDocument, Job, Step};
use emf_postgres::PgPool;
use emf_tracing::tracing;
use emf_wire_types::{Command, CommandGraphExt, CommandPlan, CommandStep, State};
use futures::{StreamExt, TryFutureExt};
use petgraph::{graph::NodeIndex, visit::IntoNodeReferences};
use std::{cmp::min, collections::HashMap, convert::TryInto, sync::Arc};
use tokio::{
    io::{BufWriter, DuplexStream},
    sync::mpsc,
};
use tokio_util::io::ReaderStream;

pub type JobGraph = petgraph::graph::DiGraph<Step, ()>;
pub type JobGraphs = petgraph::graph::DiGraph<(String, Arc<JobGraph>), ()>;

pub fn build_job_graphs(input_doc: InputDocument) -> JobGraphs {
    // Add job nodes to the job graph
    let mut job_graphs = JobGraphs::new();
    let mut job_map = HashMap::new();

    for (name, Job { steps, needs, .. }) in input_doc.jobs {
        let g = steps
            .into_iter()
            .fold((JobGraph::new(), None), |(mut g, last), step| {
                let node_idx = g.add_node(step);

                if let Some(last_idx) = last {
                    g.add_edge(last_idx, node_idx, ());
                };

                (g, Some(node_idx))
            })
            .0;

        let idx = job_graphs.add_node((name.to_string(), Arc::new(g)));
        job_map.insert(name, (idx, needs));
    }

    // Link all job nodes based on their dependencies
    for (job_index, needs) in job_map.values() {
        for need in needs {
            let idx = job_map[need].0;

            job_graphs.add_edge(idx, *job_index, ());
        }
    }

    job_graphs
}

pub async fn build_command(pg_pool: &PgPool, job_graphs: &JobGraphs) -> Result<Command, Error> {
    let plan: CommandPlan = job_graphs.map(
        |_, (name, job_graph)| {
            (
                name.to_string(),
                job_graph
                    .as_ref()
                    .map(|_, x| StepWrapper(x).into(), |_, x| *x),
            )
        },
        |_, x| *x,
    );

    let id = sqlx::query!(
        "INSERT INTO command_plan (plan) VALUES ($1) RETURNING id",
        serde_json::to_value(&plan)?
    )
    .fetch_one(pg_pool)
    .await?
    .id;

    Ok(Command {
        id,
        plan: (&plan).try_into()?,
        state: State::Pending,
    })
}

#[derive(Debug)]
pub(crate) enum Change {
    Started(DateTime<Utc>),
    Ended(DateTime<Utc>),
    State(State),
    Stdout(Bytes),
    Stderr(Bytes),
    Result(Result<String, String>),
}

struct StepWrapper<'a>(&'a Step);

impl From<StepWrapper<'_>> for CommandStep {
    fn from(StepWrapper(step): StepWrapper) -> Self {
        Self {
            action: step.action.into(),
            id: step.id.to_string(),
            msg: None,
            state: State::Pending,
            started_at: None,
            finished_at: None,
            stdout: String::new(),
            stderr: String::new(),
        }
    }
}

/// Used to send `Change`s for a given `CommandPlan`
pub(crate) type CommandPlanWriter = mpsc::UnboundedSender<(NodeIndex, NodeIndex, Change)>;

pub(crate) trait CommandPlanWriterExt {
    /// Returns a new `CommandJobWriter` That can write changes scoped to a Job
    fn get_command_job_writer(&self, job_idx: NodeIndex) -> CommandJobWriter;
}

impl CommandPlanWriterExt for CommandPlanWriter {
    fn get_command_job_writer(&self, job_idx: NodeIndex) -> CommandJobWriter {
        let (tx, mut rx) = mpsc::unbounded_channel();

        let outer_tx = self.clone();

        tokio::spawn(async move {
            while let Some((step_idx, change)) = rx.recv().await {
                let _ = outer_tx.send((job_idx, step_idx, change));
            }
        });

        tx
    }
}

pub(crate) type CommandJobWriter = mpsc::UnboundedSender<(NodeIndex, Change)>;

pub(crate) trait CommandJobWriterExt {
    /// Returns a new `CommandStepWriter` That can write changes scoped to a `CommandStep`
    fn get_command_state_writer(&self, step_idx: NodeIndex) -> CommandStepWriter;
}

impl CommandJobWriterExt for CommandJobWriter {
    fn get_command_state_writer(&self, step_idx: NodeIndex) -> CommandStepWriter {
        let (tx, mut rx) = mpsc::unbounded_channel();

        let outer_tx = self.clone();

        tokio::spawn(async move {
            while let Some(change) = rx.recv().await {
                let _ = outer_tx.send((step_idx, change));
            }
        });

        tx
    }
}

pub(crate) type CommandStepWriter = mpsc::UnboundedSender<Change>;

pub(crate) trait CommandStepWriterExt {
    /// Returns a pair of `OutputWriter`s that can write to stdout and stderr respectively for the associated `CommandStep`.
    fn get_output_handles(&self) -> (OutputWriter, OutputWriter);
    fn send_change(&self, change: Change);
}

impl CommandStepWriterExt for CommandStepWriter {
    fn get_output_handles(&self) -> (OutputWriter, OutputWriter) {
        let (stdout_tx, stdout_rx) = tokio::io::duplex(10_000);
        let (stderr_tx, stderr_rx) = tokio::io::duplex(10_000);

        let mut stdout_rx = ReaderStream::new(stdout_rx).fuse();
        let mut stderr_rx = ReaderStream::new(stderr_rx).fuse();

        let tx = self.clone();

        tokio::spawn(
            async move {
                loop {
                    tokio::select! {
                        Some(v) = stdout_rx.next() => tx.send(Change::Stdout(v?))?,
                        Some(v) = stderr_rx.next() => tx.send(Change::Stderr(v?))?,
                        else => break
                    }
                }

                Ok(())
            }
            .map_err(|e: Box<dyn std::error::Error>| {
                tracing::warn!("Could not persist stdout or stderr to DB {:?}", e)
            }),
        );

        (BufWriter::new(stdout_tx), BufWriter::new(stderr_tx))
    }
    fn send_change(&self, change: Change) {
        if let Err(e) = self.send(change) {
            tracing::warn!("Could not send change {:?} to command", e.0);
        };
    }
}

pub(crate) type OutputWriter = BufWriter<DuplexStream>;

pub(crate) async fn command_plan_writer(
    pool: &PgPool,
    plan_id: i32,
    job_graphs: &JobGraphs,
) -> Result<CommandPlanWriter, Error> {
    let (tx, mut rx) = mpsc::unbounded_channel();

    let mut command_plan: CommandPlan = job_graphs.map(
        |_, (name, job_graph)| {
            (
                name.to_string(),
                job_graph
                    .as_ref()
                    .map(|_, x| StepWrapper(x).into(), |_, x| *x),
            )
        },
        |_, x| *x,
    );

    let pool2 = pool.clone();

    tokio::spawn(async move {
        while let Some((job_idx, step_idx, change)) = rx.recv().await {
            let x = match command_plan
                .node_weight_mut(job_idx)
                .and_then(|(_, x)| x.node_weight_mut(step_idx))
            {
                Some(x) => x,
                None => {
                    tracing::warn!("Could not find node for {:?}.{:?}", job_idx, step_idx);
                    continue;
                }
            };

            match change {
                Change::Started(started_at) => {
                    x.started_at = Some(started_at);
                }
                Change::Ended(finished_at) => {
                    x.finished_at = Some(finished_at);
                }
                Change::State(state) => {
                    x.state = state;
                }
                Change::Stdout(buf) => x.stdout += &String::from_utf8_lossy(&buf),
                Change::Stderr(buf) => x.stderr += &String::from_utf8_lossy(&buf),
                Change::Result(r) => x.msg = Some(r),
            }

            let state = command_plan
                .node_references()
                .map(|(_, (_, g))| g.get_state())
                .fold(State::Completed, min);

            let x = match serde_json::to_value(&command_plan) {
                Ok(x) => x,
                Err(e) => {
                    tracing::warn!("Could not serialize command plan {:?}", e);

                    continue;
                }
            };

            let r = sqlx::query!(
                "UPDATE command_plan SET plan = $1, state = $2 WHERE id = $3",
                x,
                state as State,
                plan_id
            )
            .execute(&pool2)
            .await;

            if let Err(e) = r {
                tracing::warn!("Could not save command plan {:?}", e);
            }
        }
    });

    Ok(tx)
}
