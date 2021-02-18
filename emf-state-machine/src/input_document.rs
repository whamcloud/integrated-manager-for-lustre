// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::Error;
use once_cell::sync::Lazy;
use std::{
    collections::{BTreeSet, HashMap},
    time::Duration,
};

pub static INPUT_DOCUMENT_SCHEMA: Lazy<serde_json::Value> =
    Lazy::new(|| serde_json::from_str(std::include_str!("input-document-schema.json")).unwrap());

#[derive(serde::Serialize, serde::Deserialize)]
pub struct Step {
    action: String,
    id: String,
    inputs: Option<HashMap<String, serde_json::Value>>,
    outputs: Option<HashMap<String, serde_json::Value>>,
}

#[derive(serde::Serialize, serde::Deserialize)]
pub struct Job {
    name: String,
    #[serde(default)]
    needs: BTreeSet<String>,
    steps: Vec<Step>,
}

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(default)]
pub struct InputDocument {
    jobs: HashMap<String, Job>,
    dry_run: bool,
    #[serde(with = "humantime_serde")]
    timeout: Option<Duration>,
    refresh: bool,
}

impl Default for InputDocument {
    fn default() -> Self {
        Self {
            jobs: HashMap::default(),
            dry_run: true,
            timeout: None,
            refresh: false,
        }
    }
}

/// Parses an input document string and returns an `InputDocument` structure if successful.
pub fn parse_input_document(document: &str) -> Result<InputDocument, Error> {
    let cfg = jsonschema_valid::Config::from_schema(&INPUT_DOCUMENT_SCHEMA, None)?;
    cfg.validate_schema()?;

    let input_doc = serde_yaml::from_str::<serde_json::Value>(&document)?;
    cfg.validate(&input_doc)?;

    let input_doc: InputDocument = serde_yaml::from_str(&document)?;

    Ok(input_doc)
}

#[cfg(test)]
mod tests {
    use super::*;
    use insta::{assert_json_snapshot, assert_snapshot};

    fn mk_err_str(errs: Vec<jsonschema_valid::ValidationError>) -> String {
        let mut strings: Vec<_> = errs.into_iter().map(|x| format!("{}", x,)).collect();
        strings.sort();
        strings.join("\n\n")
    }

    #[test]
    fn invalid_input_document() -> Result<(), Error> {
        let s = r#"
version: 1
jobs:
    add_mds1:
        name: Add Mds1
        steps:
            - action: host.add
              inputs:
                  fqdn: mds1
              outputs:
                  id: this.id
    configure_lnet:
        name: configure lnet
        needs:
            - add_mds1
        steps:
            - action: lnet.configure
              id: step1
              inputs:
                  path: /dev/sfa/sda1
                  host_id: '${{needs.add_mds1.step1.outputs.id}}'
timeout: 5 minutes
"#;

        let state_schema = parse_input_document(s);
        assert!(state_schema.is_err());

        match state_schema {
            Err(Error::Schema(errs)) => {
                assert_snapshot!(mk_err_str(errs));
            }
            Err(e) => panic!(
                "Parsing input should have produced a schema validation error. Received {:?}",
                e
            ),
            Ok(_) => panic!("Should only receive an error."),
        };

        Ok(())
    }

    #[test]
    fn valid_input_document() -> Result<(), Error> {
        let s = r#"
version: 1
jobs:
    add_mds1:
        name: Add Mds1
        steps:
            - action: host.add
              id: step1
              inputs:
                  fqdn: mds1
              outputs:
                  id: this.id
    configure_lnet:
        name: configure lnet
        needs:
            - add_mds1
        steps:
            - action: lnet.configure
              id: step1
              inputs:
                  path: /dev/sfa/sda1
                  host_id: '${{needs.add_mds1.step1.outputs.id}}'
timeout: 5 minutes
"#;
        let state_schema = parse_input_document(s)?;

        insta::with_settings!({sort_maps => true}, {
            assert_json_snapshot!(state_schema);
        });

        Ok(())
    }

    #[test]
    fn valid_input_document2() -> Result<(), Error> {
        let s = r#"
version: 1
jobs:
    add_mds1:
        name: Add Mds1
        steps:
            - action: host.add
              id: step1
              inputs:
                  fqdn: mds1
              outputs:
                  id: this.id
    configure_lnet:
        name: configure lnet
        needs:
            - add_mds1
        steps:
            - action: lnet.configure
              id: step1
              inputs:
                  path: /dev/sfa/sda1
                  host_id: '${{needs.add_mds1.step1.outputs.id}}'
"#;
        let state_schema = parse_input_document(s)?;

        insta::with_settings!({sort_maps => true}, {
            assert_json_snapshot!(state_schema);
        });

        Ok(())
    }
}
