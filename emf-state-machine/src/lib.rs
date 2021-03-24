// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

pub mod action_runner;
pub mod command_plan;
pub mod executor;
pub mod transition_graph;

use emf_lib_state_machine::{
    input_document::InputDocumentErrors,
    state_schema::{self, ActionName, State},
};
use sqlx::migrate::MigrateError;
use std::{collections::HashMap, io};
use validator::{Validate, ValidationErrors};
use warp::reject;

/// The transition graph is a graph containing states for nodes and actions for edges.
type TransitionGraph = petgraph::graph::DiGraph<State, ActionName>;

#[derive(thiserror::Error, Debug)]
pub enum Error {
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::Error),
    #[error(transparent)]
    MigrateError(#[from] MigrateError),
    #[error(transparent)]
    SqlxError(#[from] sqlx::Error),
    #[error(transparent)]
    SshError(#[from] emf_ssh::Error),
    #[error(transparent)]
    InputDocumentErrors(#[from] InputDocumentErrors),
    #[error(transparent)]
    IoError(#[from] io::Error),
}

impl reject::Reject for Error {}

pub(crate) trait ValidateAddon {
    fn validate(&self) -> Result<(), ValidationErrors>;
}

impl<T: Validate> ValidateAddon for HashMap<String, T> {
    fn validate(&self) -> Result<(), ValidationErrors> {
        for i in self.values() {
            i.validate()?
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        command_plan::{build_job_graphs, OutputWriter},
        executor::build_execution_graph,
    };
    use emf_lib_state_machine::{
        input_document::{deserialize_input_document, host, SshOpts, Step, StepPair},
        state_schema::Input,
    };
    use emf_postgres::PgPool;
    use emf_wire_types::ComponentType;
    use futures::Future;
    use once_cell::sync::Lazy;
    use petgraph::{graph::NodeIndex, visit::NodeIndexable};
    use std::{ops::Deref, pin::Pin, sync::Arc};
    use tokio::sync::{mpsc, Mutex};

    #[tokio::test]
    #[ignore = "Requires an active and populated DB"]
    async fn graph_execution_stacks_population() -> Result<(), Box<dyn std::error::Error>> {
        let pool = emf_postgres::test_setup().await?;

        static GLOBAL_DATA: Lazy<Mutex<Vec<String>>> = Lazy::new(|| {
            let xs = vec![];
            Mutex::new(xs)
        });

        let input_document = r#"version: 1
jobs:
  test_job1:
    name: Test stack 1
    steps:
      - action: host.ssh_command
        id: command1
        inputs:
          host: node1
          run: command1
      - action: host.ssh_command
        id: command2
        inputs:
          host: node1
          run: command2
      - action: host.ssh_command
        id: command3
        inputs:
          host: node1
          run: command3"#;

        let doc = deserialize_input_document(input_document)?;
        let mut job_graphs = build_job_graphs(doc);
        let mut graph = job_graphs.remove_node(NodeIndex::new(0)).unwrap().1;
        let graph_ref = Arc::get_mut(&mut graph).unwrap();

        let node4 = graph_ref.add_node(Step {
            action: StepPair::new(
                ComponentType::Host,
                ActionName::Host(host::ActionName::SshCommand),
            ),
            id: "step4".into(),
            inputs: Input::Host(host::Input::SshCommand(host::SshCommand {
                host: "node1".into(),
                run: "command4".into(),
                ssh_opts: SshOpts::default(),
            })),
            outputs: None,
        });

        let node5 = graph_ref.add_node(Step {
            action: StepPair::new(
                ComponentType::Host,
                ActionName::Host(host::ActionName::SshCommand),
            ),
            id: "step5".into(),
            inputs: Input::Host(host::Input::SshCommand(host::SshCommand {
                host: "node1".into(),
                run: "command5".into(),
                ssh_opts: SshOpts::default(),
            })),
            outputs: None,
        });

        graph_ref.add_edge(graph_ref.from_index(0), node4, ());
        graph_ref.add_edge(node4, node5, ());

        fn invoke_box(
            _: PgPool,
            _: OutputWriter,
            _: OutputWriter,
            input: &Input,
        ) -> Pin<Box<dyn Future<Output = Result<(), Error>> + Send + '_>> {
            Box::pin(async move {
                match input {
                    Input::Host(host::Input::SshCommand(x)) => {
                        GLOBAL_DATA.lock().await.push(x.run.to_string())
                    }
                    _ => panic!("Should have received host ssh command."),
                }

                Ok(())
            })
        }

        let (tx, _rx) = mpsc::unbounded_channel();

        let stacks = build_execution_graph(&pool, tx, graph, invoke_box);

        // There should be exactly two stacks
        assert_eq!(stacks.len(), 2);

        // Execute the first stack. We should see that the first three commands ran.
        let mut iter = stacks.into_iter();
        iter.next().unwrap().await;

        {
            let mut items = GLOBAL_DATA.lock().await;

            assert_eq!(
                items.deref(),
                &vec![
                    "command1".to_string(),
                    "command2".to_string(),
                    "command3".to_string(),
                ]
            );

            items.clear();
        }

        // Execute the second stack. We should see that commands 4, 5, and 6 ran.
        iter.next().unwrap().await;

        let items = GLOBAL_DATA.lock().await;

        assert_eq!(
            items.deref(),
            &vec!["command4".to_string(), "command5".to_string(),]
        );

        Ok(())
    }
}
