// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::EmfAgentError;
use emf_cmd::{CheckedCommandExt, Command};
use emf_fs::file_exists;
use emf_wire_types::high_availability::{Ban, Cluster, Node, Resource};
use futures::TryFutureExt;
use quick_xml::{
    events::{attributes::Attributes, Event},
    Reader,
};
use std::{collections::HashMap, convert::TryInto, ffi::OsStr, process::Output};

static CIBADMIN_PATH: &str = "/usr/sbin/cibadmin";

fn cibadmin_cmd() -> Command {
    let mut cmd = Command::new(CIBADMIN_PATH);

    cmd.kill_on_drop(true);

    cmd
}

static CRM_MON_PATH: &str = "/usr/sbin/crm_mon";

pub(crate) fn crm_mon_cmd() -> Command {
    let mut cmd = Command::new(CRM_MON_PATH);

    cmd.arg("--one-shot")
        .arg("--inactive")
        .arg("--as-xml")
        .kill_on_drop(true);

    cmd
}

static CRM_RESOURCE_PATH: &str = "/usr/sbin/crm_resource";

fn crm_resource_cmd() -> Command {
    let mut cmd = Command::new(CRM_RESOURCE_PATH);

    cmd.kill_on_drop(true);

    cmd
}

static CRM_ATTRIBUTE_PATH: &str = "/usr/sbin/crm_attribute";

fn crm_attribute_cmd() -> Command {
    let mut cmd = Command::new(CRM_ATTRIBUTE_PATH);

    cmd.kill_on_drop(true);

    cmd
}

static PCS_PATH: &str = "/usr/sbin/pcs";

fn pcs_cmd() -> Command {
    let mut cmd = Command::new(PCS_PATH);

    cmd.kill_on_drop(true);

    cmd
}

static COROSYNC_CFGTOOL_PATH: &str = "/usr/sbin/corosync-cfgtool";

fn corosync_cfgtool() -> Command {
    let mut cmd = Command::new(COROSYNC_CFGTOOL_PATH);

    cmd.kill_on_drop(true);

    cmd
}

pub async fn get_local_nodeid() -> Result<Option<String>, EmfAgentError> {
    if !file_exists(COROSYNC_CFGTOOL_PATH).await {
        return Ok(None);
    }

    let output = corosync_cfgtool().arg("-s").checked_output().await?;

    parse_local_nodeid_output(&output.stdout)
}

fn parse_local_nodeid_output(x: &[u8]) -> Result<Option<String>, EmfAgentError> {
    let x = std::str::from_utf8(x)?;

    let prefix = "Local node ID ";

    let x = x
        .split_terminator('\n')
        .find(|x| x.starts_with(prefix))
        .and_then(|x| x.strip_prefix(prefix))
        .map(|x| x.to_string());

    Ok(x)
}

async fn get_lustre_resource_mounts(
    xs: Vec<String>,
) -> Result<HashMap<String, String>, EmfAgentError> {
    let mut out = HashMap::new();

    for x in xs {
        let output = crm_resource_cmd()
            .arg("--query-xml")
            .arg("--resource")
            .arg(&x)
            .checked_output()
            .await?;

        if let Some(v) = parse_resource_xml(&output.stdout)? {
            out.insert(x, v);
        };
    }

    Ok(out)
}

fn is_lustre_ra(x: &str) -> bool {
    x == "ocf::ddn:lustre-server" || x == "ocf::lustre:Lustre"
}

pub async fn set_resource_role(resource: &str, running: bool) -> Result<(), EmfAgentError> {
    crm_resource_cmd()
        .args(&[
            "--resource",
            resource,
            "--set-parameter",
            "target-role",
            "--meta",
            "--parameter-value",
            if running { "Started" } else { "Stopped" },
        ])
        .checked_output()
        .await?;

    Ok(())
}

pub async fn cibcreate(scope: &str, xml: &str) -> Result<(), EmfAgentError> {
    cibadmin_cmd()
        .args(&["--create", "--scope", scope, "--xml-text", xml])
        .checked_status()
        .inspect_err(|_| tracing::error!("Failed to create {}: {}", scope, xml))
        .err_into()
        .await
}

pub async fn cibxpath<I, S>(op: &str, xpath: &str, extra: I) -> Result<String, EmfAgentError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let o = cibadmin_cmd()
        .arg(format!("--{}", op))
        .arg("--xpath")
        .arg(xpath)
        .args(extra)
        .checked_output()
        .await?;

    Ok(String::from_utf8_lossy(&o.stdout).to_string())
}

pub async fn crm_resource<I, S>(args: I) -> Result<String, EmfAgentError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let o = crm_resource_cmd().args(args).checked_output().await?;

    Ok(String::from_utf8_lossy(&o.stdout).to_string())
}

pub async fn crm_attribute(args: Vec<String>) -> Result<String, EmfAgentError> {
    let o = crm_attribute_cmd().args(args).checked_output().await?;

    Ok(String::from_utf8_lossy(&o.stdout).to_string())
}

pub async fn pcs(args: Vec<String>) -> Result<String, EmfAgentError> {
    let o = pcs_cmd().args(args).checked_output().await?;

    Ok(String::from_utf8_lossy(&o.stdout).to_string())
}

pub async fn get_crm_mon_output() -> Result<Output, emf_cmd::CmdError> {
    crm_mon_cmd().checked_output().await
}

pub async fn get_crm_mon() -> Result<Option<Cluster>, EmfAgentError> {
    if !file_exists(CRM_MON_PATH).await {
        return Ok(None);
    }

    let crm_output = get_crm_mon_output().await?;

    let mut x = read_crm_output(&crm_output.stdout)?;

    let lustre_resource_ids = x
        .resources
        .iter()
        .filter_map(|x| {
            if is_lustre_ra(&x.resource_agent) {
                Some(x.id.to_string())
            } else {
                None
            }
        })
        .collect();

    let mounts = get_lustre_resource_mounts(lustre_resource_ids).await?;

    x.resource_mounts = mounts;

    let ban_output = crm_mon_cmd()
        .arg("--neg-locations")
        .checked_output()
        .await?;

    read_banned_output(&ban_output.stdout, &mut x)?;

    Ok(Some(x))
}

fn required_arg<'a>(arg: &str, x: &'a HashMap<&str, String>) -> Result<&'a str, EmfAgentError> {
    x.get(arg)
        .map(|x| x.as_str())
        .ok_or_else(|| EmfAgentError::MissingArgument(arg.into()))
}

fn required_bool(arg: &str, x: &HashMap<&str, String>) -> Result<bool, EmfAgentError> {
    let x = required_arg(arg, x)?;
    let x = x.parse()?;

    Ok(x)
}

fn node_from_map(x: &HashMap<&str, String>) -> Result<Node, EmfAgentError> {
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

fn resource_from_map(x: &HashMap<&str, String>) -> Result<Resource, EmfAgentError> {
    Ok(Resource {
        id: required_arg("id", x)?.to_string(),
        resource_agent: required_arg("resource_agent", x)?.to_string(),
        role: required_arg("role", x)?.to_string(),
        active: required_bool("active", x)?,
        orphaned: required_bool("orphaned", x)?,
        managed: required_bool("managed", x)?,
        failed: required_bool("failed", x)?,
        failure_ignored: required_bool("failure_ignored", x)?,
        nodes_running_on: required_arg("nodes_running_on", x)?.parse::<u32>()?,
        active_node_id: None,
        active_node_name: None,
    })
}

fn ban_from_map(x: &HashMap<&str, String>) -> Result<Ban, EmfAgentError> {
    Ok(Ban {
        id: required_arg("id", x)?.to_string(),
        resource: required_arg("resource", x)?.to_string(),
        node: required_arg("node", x)?.to_string(),
        weight: required_arg("weight", x)?.parse::<i32>()?,
        master_only: required_bool("master_only", x)?,
    })
}

fn attrs_to_hashmap<'a>(
    mut attrs: Attributes<'a>,
    reader: &Reader<&[u8]>,
) -> Result<HashMap<&'a str, String>, EmfAgentError> {
    attrs.try_fold(HashMap::new(), |mut acc, x| {
        let x = x?;

        acc.insert(
            std::str::from_utf8(x.key)?,
            x.unescape_and_decode_value(reader)?,
        );

        Ok(acc)
    })
}

fn read_nodes(reader: &mut Reader<&[u8]>) -> Result<Vec<Node>, EmfAgentError> {
    let mut buf = vec![];
    let mut xs = vec![];

    loop {
        buf.clear();

        match reader.read_event(&mut buf)? {
            Event::Empty(x) if x.name() == b"node" => {
                let x = attrs_to_hashmap(x.attributes(), reader)?;
                let x = node_from_map(&x)?;

                xs.push(x);
            }
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

enum Ra {
    Ddn(Option<String>),
    Lustre(Option<String>),
}

impl Ra {
    fn inner(self) -> Option<String> {
        match self {
            Self::Ddn(x) => x,
            Self::Lustre(x) => x,
        }
    }
}

fn parse_resource_xml(x: &[u8]) -> Result<Option<String>, EmfAgentError> {
    let x = std::str::from_utf8(x)?;

    let xs: Vec<_> = x.trim().lines().skip(2).collect();

    if xs.is_empty() {
        return Ok(None);
    }

    let x = xs.join("\n");
    let mut reader = Reader::from_str(&x);
    reader.trim_text(true);

    let mut buf = vec![];

    let mut current_ra = None;

    loop {
        match reader.read_event(&mut buf)? {
            Event::Start(ref x) if x.name() == b"primitive" => {
                let mut x = attrs_to_hashmap(x.attributes(), &reader)?;

                match (
                    x.remove("class").as_deref(),
                    x.remove("provider").as_deref(),
                    x.remove("type").as_deref(),
                ) {
                    (Some("ocf"), Some("ddn"), Some("lustre-server")) => {
                        current_ra = Some(Ra::Ddn(None));
                    }
                    (Some("ocf"), Some("lustre"), Some("Lustre")) => {
                        current_ra = Some(Ra::Lustre(None));
                    }
                    _ => {}
                }
            }
            Event::Empty(ref x) if x.name() == b"nvpair" => {
                let mut x = attrs_to_hashmap(x.attributes(), &reader)?;

                match current_ra.as_mut() {
                    Some(Ra::Ddn(ref mut v)) => {
                        if x.remove("name") == Some("directory".into()) {
                            *v = x.remove("value");
                        }
                    }
                    Some(Ra::Lustre(ref mut v)) => {
                        if x.remove("name") == Some("mountpoint".into()) {
                            *v = x.remove("value");
                        }
                    }
                    _ => {}
                }
            }

            Event::Eof => break,
            _ => {}
        };

        buf.clear();
    }

    Ok(current_ra.and_then(|x| x.inner()))
}

fn read_resources(reader: &mut Reader<&[u8]>) -> Result<Vec<Resource>, EmfAgentError> {
    let mut buf = vec![];
    let mut xs = vec![];

    let mut current_resource = None;
    let mut clone_index = -1;

    loop {
        buf.clear();

        match reader.read_event(&mut buf)? {
            Event::Start(x) => match x.name() {
                b"resource" => {
                    let x = attrs_to_hashmap(x.attributes(), reader)?;

                    current_resource = Some(resource_from_map(&x)?);
                }
                b"clone" => {
                    clone_index = 0;
                }
                _ => {}
            },
            Event::Empty(x) => match x.name() {
                b"node" => {
                    let mut x = attrs_to_hashmap(x.attributes(), reader)?;

                    if let Some(current_resource) = current_resource.as_mut() {
                        current_resource.active_node_name = x.remove("name");
                        current_resource.active_node_id = x.remove("id");
                    }
                }
                b"resource" => {
                    let x = attrs_to_hashmap(x.attributes(), reader)?;
                    let mut r = resource_from_map(&x)?;
                    if clone_index >= 0 {
                        r.id = format!("{}:{}", &r.id, clone_index);
                        clone_index += 1;
                    }

                    xs.push(r);
                }
                _ => {}
            },
            Event::End(x) => match x.name() {
                b"resource" => {
                    if let Some(mut x) = current_resource.take() {
                        if clone_index >= 0 {
                            x.id = format!("{}:{}", &x.id, clone_index);
                            clone_index += 1;
                        }
                        xs.push(x);
                    }
                }
                b"clone" => {
                    clone_index = -1;
                }
                b"resources" => {
                    break;
                }
                _ => {}
            },
            _ => {}
        }
    }

    Ok(xs)
}

fn read_bans(reader: &mut Reader<&[u8]>) -> Result<Vec<Ban>, EmfAgentError> {
    let mut buf = vec![];
    let mut xs = vec![];

    loop {
        buf.clear();

        match reader.read_event(&mut buf)? {
            Event::Empty(x) if x.name() == b"ban" => {
                let x = attrs_to_hashmap(x.attributes(), reader)?;
                let x = ban_from_map(&x)?;

                xs.push(x);
            }
            Event::End(x) if x.name() == b"bans" => {
                break;
            }
            _ => {}
        }
    }

    Ok(xs)
}

pub(crate) fn read_crm_output(crm_output: &[u8]) -> Result<Cluster, EmfAgentError> {
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
                b"resources" => {
                    cluster.resources = read_resources(&mut reader)?;
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

fn read_banned_output(crm_output: &[u8], cluster: &mut Cluster) -> Result<(), EmfAgentError> {
    let x = std::str::from_utf8(crm_output)?;

    let mut reader = Reader::from_str(x);
    reader.trim_text(true);

    let mut buf = vec![];

    loop {
        match reader.read_event(&mut buf)? {
            Event::Start(ref x) if x.name() == b"bans" => {
                cluster.bans = read_bans(&mut reader)?;
            }
            Event::Eof => break,
            _ => {}
        };

        buf.clear();
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    static ES_FIXTURE: &'static [u8] = include_bytes!("./fixtures/es_fixture.xml");
    static ES_BAN_FIXTURE: &'static [u8] = include_bytes!("./fixtures/es_ban_fixture.xml");
    static ES_LUSTRE_RESOURCE_MOUNTS_FIXTURE: &'static [u8] =
        include_bytes!("./fixtures/es_lustre_resource_mounts_fixture.txt");
    static VAGRANT_FIXTURE: &'static [u8] = include_bytes!("./fixtures/vagrant_fixture.xml");
    static VAGRANT_STOPPED_FIXTURE: &'static [u8] =
        include_bytes!("./fixtures/vagrant_stopped_fixture.xml");
    static COROSYNC_CFGTOOL_FIXTURE: &'static [u8] =
        include_bytes!("./fixtures/corosync_cfgtool_fixture.txt");

    #[test]
    fn test_read_es() {
        let mut cluster = read_crm_output(ES_FIXTURE).unwrap();

        read_banned_output(ES_BAN_FIXTURE, &mut cluster).unwrap();

        insta::assert_debug_snapshot!(cluster);
    }

    #[test]
    fn test_read_vagrant() {
        let cluster = read_crm_output(VAGRANT_FIXTURE).unwrap();

        insta::assert_debug_snapshot!(cluster);
    }

    #[test]
    fn test_read_vagrant_stopped() {
        let cluster = read_crm_output(VAGRANT_STOPPED_FIXTURE).unwrap();

        insta::assert_debug_snapshot!(cluster);
    }

    #[test]
    fn test_lustre_resource_mounts_output() {
        let x = parse_resource_xml(ES_LUSTRE_RESOURCE_MOUNTS_FIXTURE).unwrap();

        insta::assert_debug_snapshot!(x);
    }

    #[test]
    fn test_local_nodeid_output() {
        let x = parse_local_nodeid_output(COROSYNC_CFGTOOL_FIXTURE).unwrap();

        insta::assert_debug_snapshot!(x);
    }
}
