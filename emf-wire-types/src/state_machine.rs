// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::json::GraphQLJson;
use chrono::{DateTime, Utc};
use petgraph::visit::IntoNodeReferences;
use std::{cmp::max, convert::TryFrom, fmt, time::Duration};

pub type CommandGraph = petgraph::graph::DiGraph<CommandStep, ()>;
pub type CommandPlan = petgraph::graph::DiGraph<(String, CommandGraph), ()>;

pub trait CommandGraphExt {
    fn get_state(&self) -> State;
}

impl CommandGraphExt for CommandGraph {
    fn get_state(&self) -> State {
        self.node_references()
            .map(|(_, n)| n.state)
            .fold(State::Pending, max)
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct Command {
    pub id: i32,
    pub plan: GraphQLJson,
    pub state: State,
}

#[derive(Clone, serde::Deserialize, serde::Serialize)]
pub struct CommandStep {
    pub action: String,
    pub id: String,
    pub state: State,
    pub msg: Option<Result<String, String>>,
    pub started_at: Option<DateTime<Utc>>,
    pub finished_at: Option<DateTime<Utc>>,
    pub stdout: String,
    pub stderr: String,
}

impl CommandStep {
    pub fn duration(&self) -> Option<Duration> {
        self.started_at
            .zip(self.finished_at)
            .map(|(start, end)| end - start)
            .map(|x| x.to_std())
            .transpose()
            .ok()
            .flatten()
    }
}

impl TryFrom<&CommandPlan> for GraphQLJson {
    type Error = serde_json::Error;

    fn try_from(g: &CommandPlan) -> Result<Self, Self::Error> {
        serde_json::to_value(g).map(Self)
    }
}

impl TryFrom<GraphQLJson> for CommandPlan {
    type Error = serde_json::Error;

    fn try_from(g: GraphQLJson) -> Result<Self, Self::Error> {
        serde_json::from_value(g.0)
    }
}

#[derive(
    Debug, Clone, Copy, serde::Serialize, serde::Deserialize, Eq, PartialEq, Ord, PartialOrd,
)]
#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
#[cfg_attr(feature = "postgres-interop", sqlx(rename_all = "lowercase"))]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
#[serde(rename_all = "lowercase")]
pub enum State {
    #[cfg_attr(feature = "graphql", graphql(name = "pending"))]
    Pending,
    #[cfg_attr(feature = "graphql", graphql(name = "running"))]
    Running,
    #[cfg_attr(feature = "graphql", graphql(name = "completed"))]
    Completed,
    #[cfg_attr(feature = "graphql", graphql(name = "failed"))]
    Failed,
    #[cfg_attr(feature = "graphql", graphql(name = "canceled"))]
    Canceled,
}

impl fmt::Display for State {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x = match self {
            Self::Pending => "pending",
            Self::Running => "running",
            Self::Completed => "completed",
            Self::Canceled => "canceled",
            Self::Failed => "failed",
        };

        write!(f, "{}", x)
    }
}
