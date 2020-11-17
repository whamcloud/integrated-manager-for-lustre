// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::snapshot::{Create, Destroy, Mount, Unmount};
use chrono::Utc;

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, Copy, Eq, PartialEq, Hash)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
pub enum Transition {
    CreateSnapshot,
    MountSnapshot,
    UnmountSnapshot,
    RemoveSnapshot,
}

impl Transition {
    pub fn description(&self) -> &str {
        match self {
            Self::CreateSnapshot => "Create Snapshot",
            Self::MountSnapshot => "Mount snapshot",
            Self::UnmountSnapshot => "Unmount snapshot",
            Self::RemoveSnapshot => "Remove snapshot",
        }
    }
}

impl From<Transition> for Edge {
    fn from(x: Transition) -> Edge {
        Edge::Transition(x)
    }
}

#[derive(
    serde::Serialize, serde::Deserialize, Debug, Clone, Copy, Eq, PartialEq, Ord, PartialOrd, Hash,
)]
pub enum State {
    Snapshot(snapshot::State),
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Edge {
    Transition(Transition),
    Dependency(State),
}

impl Edge {
    pub fn is_transition(&self) -> bool {
        match self {
            Self::Transition(_) => true,
            Self::Dependency(_) => false,
        }
    }
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone)]
pub enum Job {
    CreateSnapshotJob(Create),
    MountSnapshotJob(Mount),
    UnmountSnapshotJob(Unmount),
    RemoveSnapshotJob(Destroy),
}

#[cfg_attr(feature = "postgres-interop", derive(sqlx::Type))]
#[cfg_attr(feature = "postgres-interop", sqlx(rename = "machine_state"))]
#[cfg_attr(feature = "postgres-interop", sqlx(rename_all = "lowercase"))]
#[derive(serde::Deserialize, serde::Serialize, Clone, Copy, PartialEq, Debug)]
#[serde(rename_all = "lowercase")]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLEnum))]
pub enum CurrentState {
    Pending,
    Progress,
    Failed,
    Succeeded,
    Cancelled,
}

#[derive(serde::Serialize, serde::Deserialize)]
pub struct Command {
    pub message: String,
    pub jobs: Vec<Job>,
}

#[derive(serde::Serialize, serde::Deserialize)]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLObject))]
pub struct CommandRecord {
    pub id: i32,
    pub start_time: chrono::DateTime<Utc>,
    pub end_time: Option<chrono::DateTime<Utc>>,
    pub state: CurrentState,
    pub message: String,
    pub jobs: Vec<i32>,
}

pub mod snapshot {
    use crate::state_machine;

    #[derive(
        serde::Serialize,
        serde::Deserialize,
        Debug,
        Clone,
        Copy,
        Eq,
        PartialEq,
        Ord,
        PartialOrd,
        Hash,
    )]
    pub enum State {
        Unknown,
        Unmounted,
        Mounted,
        Removed,
    }

    impl Default for State {
        fn default() -> Self {
            Self::Unknown
        }
    }

    impl From<State> for state_machine::State {
        fn from(x: State) -> state_machine::State {
            state_machine::State::Snapshot(x)
        }
    }
}
