// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

pub mod action_runner;
pub mod input_document;
pub mod state_schema;
pub mod transition_graph;

use crate::{
    input_document::InputDocumentErrors,
    state_schema::{ActionName, State},
};
use emf_wire_types::Command;
use input_document::InputDocument;
use sqlx::migrate::MigrateError;
use std::collections::HashMap;
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
    InputDocumentErrors(#[from] InputDocumentErrors),
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
