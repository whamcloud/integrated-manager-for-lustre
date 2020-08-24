// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use iml_cmd::{CheckedCommandExt, Command};
use iml_fs::file_exists;
use iml_wire_types::high_availability::{Cluster, Node};
use quick_xml::{
    events::{attributes::Attributes, Event},
    Reader,
};
use std::{collections::HashMap, convert::TryInto};

static CRM_MON_PATH: &'static str = "/usr/sbin/crm_mon";

pub async fn get_crm_mon() -> Result<Option<Cluster>, ImlAgentError> {
    if !file_exists(CRM_MON_PATH).await {
        return Ok(None);
    }

    let x = Command::new(CRM_MON_PATH)
        .arg("-1")
        .arg("-r")
        .arg("-X")
        .checked_output()
        .await?;

    let x = read_crm_output(&x.stdout)?;

    Ok(Some(x))
}

fn required_arg<'a>(arg: &str, x: &'a HashMap<&str, String>) -> Result<&'a str, ImlAgentError> {
    x.get(arg)
        .map(|x| x.as_str())
        .ok_or_else(|| ImlAgentError::MissingArgument(arg.into()))
}

fn required_bool(arg: &str, x: &HashMap<&str, String>) -> Result<bool, ImlAgentError> {
    let x = required_arg(arg, x)?;
    let x = x.parse()?;

    Ok(x)
}

fn node_from_map(x: &HashMap<&str, String>) -> Result<Node, ImlAgentError> {
    Ok(Node {
        name: required_arg("name", x)?.to_string(),
        id: required_arg("id", x)?.to_string(),
        online: required_bool("online", x)?,
        standby: required_bool("standby", x)?,
        standby_onfail: required_bool("standby_onfail", x)?,
        maintenance: required_bool("maintenance", x)?,
        pending: required_bool("pending", x)?,
        unclean: required_bool("unclean", x)?,
        shutdown: required_bool("shutdown", x)?,
        expected_up: required_bool("expected_up", x)?,
        is_dc: required_bool("is_dc", x)?,
        resources_running: required_arg("resources_running", x)?.parse::<u32>()?,
        r#type: required_arg("type", x)?.try_into()?,
    })
}

fn attrs_to_hashmap<'a>(
    mut attrs: Attributes<'a>,
    reader: &Reader<&[u8]>,
) -> Result<HashMap<&'a str, String>, ImlAgentError> {
    attrs.try_fold(HashMap::new(), |mut acc, x| {
        let x = x?;

        acc.insert(
            std::str::from_utf8(x.key)?,
            x.unescape_and_decode_value(reader)?,
        );

        Ok(acc)
    })
}

fn read_nodes(reader: &mut Reader<&[u8]>) -> Result<Vec<Node>, ImlAgentError> {
    let mut buf = vec![];
    let mut xs = vec![];

    loop {
        buf.clear();

        match reader.read_event(&mut buf)? {
            Event::Empty(x) => match x.name() {
                b"node" => {
                    let x = attrs_to_hashmap(x.attributes(), reader)?;
                    let x = node_from_map(&x)?;

                    xs.push(x);
                }
                _ => {}
            },
            Event::End(x) => {
                if x.name() == b"nodes" {
                    break;
                }
            }
            _ => {}
        }
    }

    Ok(xs)
}

fn read_crm_output(crm_output: &[u8]) -> Result<Cluster, ImlAgentError> {
    let x = std::str::from_utf8(crm_output)?;

    let mut reader = Reader::from_str(x);
    reader.trim_text(true);

    let mut buf = vec![];

    let mut cluster = Cluster::default();

    loop {
        match reader.read_event(&mut buf)? {
            Event::Start(ref x) => match x.name() {
                b"nodes" => {
                    cluster.nodes = read_nodes(&mut reader)?;
                }
                _ => {}
            },
            Event::Eof => break,
            _ => {}
        };

        buf.clear();
    }

    Ok(cluster)
}

#[cfg(test)]
mod tests {
    use super::*;

    static ES_FIXTURE: &'static [u8] = include_bytes!("./fixtures/es_fixture.xml");

    #[test]
    fn test_read_es() {
        let output = read_crm_output(ES_FIXTURE).unwrap();

        insta::assert_debug_snapshot!(output);
    }
}
