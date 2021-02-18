// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::Error;
use std::{
    collections::{BTreeSet, HashMap},
    time::Duration,
};

#[derive(serde::Serialize, serde::Deserialize, Eq, PartialEq)]
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
    timeout: Duration,
    refresh: bool,
}

impl Default for InputDocument {
    fn default() -> Self {
        Self {
            jobs: HashMap::default(),
            dry_run: true,
            timeout: Duration::from_secs(60),
            refresh: false,
        }
    }
}

/// Parses an input document string and returns an `InputDocument` structure if successful.
pub fn parse_input_document(document: &str) -> Result<InputDocument, Error> {
    let input_doc: InputDocument = serde_yaml::from_str(&document)?;

    Ok(input_doc)
}

#[cfg(test)]
mod tests {
    use super::*;
    use insta::assert_json_snapshot;

    #[test]
    fn test_parse_input_document() -> Result<(), Error> {
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
}
