// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

pub mod input_document;
pub mod state_schema;
pub mod transition_graph;

use once_cell::sync::Lazy;

static STATE_SCHEMA_RAW: &str = std::include_str!("state-schema.yml");
static STATE_SCHEMA_SCHEMA_RAW: &str = std::include_str!("state-schema-schema.json");

pub static STATE_SCHEMA: Lazy<serde_json::Value> =
    Lazy::new(|| load_schema_yaml(STATE_SCHEMA_RAW, STATE_SCHEMA_SCHEMA_RAW).unwrap());

/// The transition graph is a graph containing states for nodes and actions for edges.
type TransitionGraph = petgraph::graph::DiGraph<String, String>;

#[derive(thiserror::Error, Debug)]
pub enum Error {
    #[error("invalid JSON: {0}")]
    JSON(#[from] serde_json::Error),
    #[error("invalid YAML: {0}")]
    YAML(#[from] serde_yaml::Error),
    #[error("invalid document: {0:?}")]
    Schema(Vec<jsonschema_valid::ValidationError>),
    #[error("input output error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("Error converting: {0}")]
    ConversionError(String),
}

impl From<jsonschema_valid::ValidationError> for Error {
    fn from(err: jsonschema_valid::ValidationError) -> Self {
        Error::Schema(vec![err])
    }
}

impl<'a> From<jsonschema_valid::ErrorIterator<'a>> for Error {
    fn from(i: jsonschema_valid::ErrorIterator<'a>) -> Self {
        Error::Schema(i.collect())
    }
}

fn load_schema_yaml(data_raw: &str, schema_raw: &str) -> Result<serde_json::Value, Error> {
    let schema_json = serde_json::from_str(schema_raw)?;
    let cfg = jsonschema_valid::Config::from_schema(&schema_json, None)?;
    cfg.validate_schema()?;

    let data_json = serde_yaml::from_str::<serde_json::Value>(data_raw)?;
    cfg.validate(&data_json)?;

    Ok(data_json)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mk_err_str(errs: Vec<jsonschema_valid::ValidationError>) -> String {
        let mut strings: Vec<_> = errs.into_iter().map(|x| format!("{}", x,)).collect();
        strings.sort();
        strings.join("\n\n")
    }

    #[test]
    fn invalid_state_schema_is_invalid() {
        let s = r#"
version: s
components:
  lnet:
    states:
      up:
      down:
    actions:
      start:
        state:
          start: own
          ed: oops
      stop:
        state:
          start: up
          end: down
"#;
        let state_schema = load_schema_yaml(s, STATE_SCHEMA_SCHEMA_RAW);
        assert!(state_schema.is_err());

        match state_schema.unwrap_err() {
            Error::Schema(errs) => {
                insta::assert_snapshot!(mk_err_str(errs));
            }
            e => {
                panic!("Unexpected error: {:?}", e);
            }
        }
    }

    #[test]
    fn state_schema_is_valid() -> Result<(), Error> {
        load_schema_yaml(STATE_SCHEMA_RAW, STATE_SCHEMA_SCHEMA_RAW).map(drop)
    }
}
