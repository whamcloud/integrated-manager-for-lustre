// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output_success};
use elementtree::Element;
use iml_wire_types::{ResourceAgentInfo, ResourceAgentType};
use std::collections::HashMap;

fn create(elem: &Element, group: Option<String>) -> ResourceAgentInfo {
    ResourceAgentInfo {
        agent: ResourceAgentType::new(
            elem.get_attr("class").unwrap_or("").to_string(),
            elem.get_attr("provider").map(|s| s.to_string()),
            elem.get_attr("type").unwrap_or("").to_string(),
        ),
        group,
        id: elem.get_attr("id").unwrap_or("").to_string(),
        args: match elem.find("instance_attributes") {
            None => HashMap::new(),
            Some(e) => e
                .find_all("nvpair")
                .map(|nv| {
                    (
                        nv.get_attr("name").unwrap_or("").to_string(),
                        nv.get_attr("value").unwrap_or("").to_string(),
                    )
                })
                .collect(),
        },
    }
}

fn process_resources(xml: &[u8]) -> Result<Vec<ResourceAgentInfo>, ImlAgentError> {
    // This cannot split between map/map_err because Element does not implement Send
    match Element::from_reader(xml) {
        Err(err) => Err(ImlAgentError::XmlError(err)),
        Ok(elem) => Ok(elem
            .find_all("group")
            .flat_map(|g| {
                let name = g.get_attr("id").unwrap_or("").to_string();
                g.find_all("primitive")
                    .map(move |p| create(p, Some(name.clone())))
            })
            .chain(elem.find_all("primitive").map(|p| create(p, None)))
            .collect()),
    }
}

pub async fn check_ha(_: ()) -> Result<Vec<ResourceAgentInfo>, ImlAgentError> {
    cmd_output_success("cibadmin", vec!["--query", "--xpath", "//resources"])
        .await
        .and_then(|output| process_resources(output.stdout.as_slice()))
}

#[cfg(test)]
mod tests {
    use super::process_resources;

    #[test]
    fn test_good() {
        let testxml = include_bytes!("testing/cibadmin-resources.xml");

        let res = process_resources(testxml).unwrap();

        assert_eq!(res.len(), 6);
    }
}
