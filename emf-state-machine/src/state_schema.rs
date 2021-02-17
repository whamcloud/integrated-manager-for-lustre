// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::Error;
use emf_wire_types::ComponentType;
use std::{
    collections::{BTreeMap, BTreeSet},
    convert::TryFrom,
};

static STATE_SCHEMA: &str = std::include_str!("state-schema.yml");

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct ActionState {
    #[serde(default)]
    pub start: Option<BTreeSet<String>>,
    pub end: String,
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct Action {
    pub input: Option<serde_yaml::Value>,
    #[serde(default)]
    pub provisional: bool,
    pub state: ActionState,
}

#[derive(Clone, Debug, serde::Deserialize, Eq, Ord, PartialEq, PartialOrd, serde::Serialize)]
#[serde(try_from = "serde_json::Map<String, serde_json::Value>")]
pub struct DepNode {
    pub name: String,
    pub state: String,
}

impl TryFrom<serde_json::Map<String, serde_json::Value>> for DepNode {
    type Error = crate::Error;

    fn try_from(x: serde_json::Map<String, serde_json::Value>) -> Result<Self, Error> {
        let (name, state) = x
            .into_iter()
            .next()
            .ok_or_else(|| crate::Error::ConversionError("No Dep Node found.".into()))?;

        Ok(Self {
            name,
            state: state
                .as_str()
                .ok_or_else(|| {
                    crate::Error::ConversionError("State is missing for Dep Node.".into())
                })?
                .to_string(),
        })
    }
}

#[derive(Clone, Debug, serde::Deserialize, Eq, Ord, PartialEq, PartialOrd, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Dependency {
    Or(BTreeSet<DepNode>),
    All(BTreeSet<DepNode>),
    Exactly(DepNode),
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct ComponentState {
    #[serde(default)]
    dependencies: Option<Vec<Dependency>>,
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct Component {
    pub states: BTreeMap<String, Option<ComponentState>>,
    pub actions: BTreeMap<String, Action>,
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct Schema {
    pub components: BTreeMap<ComponentType, Component>,
}

pub fn parse_state_schema() -> Result<Schema, Error> {
    let schema: Schema = serde_yaml::from_str(&STATE_SCHEMA)?;

    Ok(schema)
}

#[cfg(test)]
mod tests {
    use super::*;
    use insta::assert_json_snapshot;

    #[test]
    fn parse_schema() -> Result<(), Error> {
        let schema = parse_state_schema()?;

        insta::with_settings!({sort_maps => true}, {
            assert_json_snapshot!(schema);
        });

        Ok(())
    }
}
