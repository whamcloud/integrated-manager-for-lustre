// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub(crate) mod corosync_conf;
pub(crate) mod pacemaker;

use crate::{
    agent_error::{ImlAgentError, RequiredError},
    high_availability::{
        cibcreate, cibxpath, crm_mon_cmd, crm_resource, read_crm_output, set_resource_role,
    },
};
use elementtree::Element;
use futures::{future::try_join_all, try_join};
use iml_cmd::{CheckedCommandExt, Command};
use iml_fs::file_exists;
use iml_wire_types::{
    ComponentState, ConfigState, LossPolicy, PacemakerActions, PacemakerKindOrScore,
    PacemakerOperations, PacemakerScore, ResourceAgentInfo, ResourceAgentType, ResourceConstraint,
    ServiceState,
};
use std::{collections::HashMap, time::Duration};
use tokio::time::delay_for;

pub use crate::high_availability::{crm_attribute, pcs};

const NO_EXTRA: Vec<String> = vec![];

const WAIT_SEC: u64 = 300;
const WAIT_DELAY: u64 = 2;

fn create(elem: &Element) -> ResourceAgentInfo {
    ResourceAgentInfo {
        agent: {
            ResourceAgentType::new(
                elem.get_attr("class"),
                elem.get_attr("provider"),
                elem.get_attr("type"),
            )
        },
        id: elem.get_attr("id").unwrap_or_default().to_string(),
        args: elem
            .find_all("instance_attributes")
            .map(|e| {
                e.find_all("nvpair").map(|nv| {
                    (
                        nv.get_attr("name").unwrap_or_default().to_string(),
                        nv.get_attr("value").unwrap_or_default().to_string(),
                    )
                })
            })
            .flatten()
            .collect(),
        ops: {
            // "stop"|"start"|"monitor" => (interval, timeout)
            let mut ops: HashMap<&str, (Option<String>, Option<String>)> = elem
                .find_all("operations")
                .map(|e| {
                    e.find_all("op").map(|nv| {
                        (
                            nv.get_attr("name").unwrap_or_default(),
                            (
                                nv.get_attr("interval").map(str::to_string),
                                nv.get_attr("timeout").map(str::to_string),
                            ),
                        )
                    })
                })
                .flatten()
                .collect();
            PacemakerOperations::new(
                ops.remove("start").map(|e| e.1).flatten(),
                ops.remove("monitor").map(|e| e.0).flatten(),
                ops.remove("stop").map(|e| e.1).flatten(),
            )
        },
    }
}

async fn wait_resource(resource: &str, running: bool) -> Result<(), ImlAgentError> {
    let sec_to_wait = WAIT_SEC;
    let sec_delay = WAIT_DELAY;
    let delay_duration = Duration::new(sec_delay, 0);
    for _ in 0..(sec_to_wait / sec_delay) {
        let output = crm_mon_cmd().checked_output().await?;

        let cluster = read_crm_output(&output.stdout)?;

        let check = if running { "Started" } else { "Stopped" };

        let mut stati = cluster
            .resources
            .into_iter()
            .filter_map(|r| {
                let id = r.id.split(':').next().unwrap_or("");
                if id == resource {
                    Some(r.role)
                } else {
                    None
                }
            })
            .peekable();
        if stati.peek() != None && stati.all(|s| s == check) {
            return Ok(());
        }
        delay_for(delay_duration).await;
    }
    Err(ImlAgentError::from(RequiredError(format!(
        "Waiting for resource {} of {} failed after {} sec",
        if running { "start" } else { "stop" },
        resource,
        sec_to_wait,
    ))))
}

fn process_resource(output: &[u8]) -> Result<ResourceAgentInfo, ImlAgentError> {
    let element = Element::from_reader(output)?;

    Ok(create(&element))
}

async fn resource_list() -> Result<Vec<String>, ImlAgentError> {
    let resources = match crm_resource(&["--list-raw"]).await {
        Ok(res) => res,
        Err(e) => {
            tracing::info!("Failed to get resource list: {:?}", e);
            return Ok(vec![]);
        }
    };

    Ok(resources
        .trim()
        .lines()
        .filter(|res| {
            // This filters out cloned resources which show up as:
            // clones-resource:0
            // clones-resource:1
            // ...
            // ":" is not valid in normal resource ids so only ":0" should be processed
            if let Some(n) = res.split(':').nth(1) {
                n.parse() == Ok(0)
            } else {
                true
            }
        })
        .map(str::to_string)
        .collect())
}

pub async fn get_ha_resource_list(_: ()) -> Result<Vec<ResourceAgentInfo>, ImlAgentError> {
    let xs = resource_list().await?.into_iter().map(|res| async move {
        let output = crm_resource(&["--query-xml", "--resource", &res]).await?;
        if let Some(xml) = output.split("xml:").last() {
            process_resource(xml.as_bytes())
        } else {
            Err(ImlAgentError::MarkerNotFound)
        }
    });
    try_join_all(xs).await
}

fn xml_add_op(
    res: &mut Element,
    id: &str,
    name: &str,
    timeout: &Option<String>,
    interval: &Option<String>,
) {
    if timeout.is_none() && interval.is_none() {
        return;
    }

    let op = res.append_new_child("op");
    op.set_attr("name", name);
    if let Some(value) = interval {
        op.set_attr("id", format!("{}-{}-interval-{}", id, name, value))
            .set_attr("interval", value);
    } else {
        // Interval is ALWAYS required
        op.set_attr("interval", "0");
    }
    if let Some(value) = timeout {
        op.set_attr("id", format!("{}-{}-timeout-{}", id, name, value))
            .set_attr("timeout", value);
    }
}

fn xml_add_nvpair(elem: &mut Element, id: &str, name: &str, value: &str) {
    let nvpair = elem.append_new_child("nvpair");
    nvpair
        .set_attr("id", format!("{}-{}", &id, name))
        .set_attr("name", name)
        .set_attr("value", value);
}

pub async fn create_single_resource(
    (agent, constraints): (ResourceAgentInfo, Vec<ResourceConstraint>),
) -> Result<(), ImlAgentError> {
    let ids = resource_list().await?;

    if ids.contains(&agent.id) {
        return Ok(());
    }

    create_resource(agent, false, constraints, true).await
}

pub async fn destroy_cloned_client(fsname: String) -> Result<(), ImlAgentError> {
    let ids = resource_list().await?;

    let id = format!("cl-{}-client", fsname);

    if !ids.contains(&format!("{}-client:0", fsname)) {
        return Ok(());
    }

    let mut paths = vec![];

    // Remove constraints added in create_clone_client()
    if let Ok(o) = cibxpath("query", "//template[@type=\"lustre-server\"]", &["-e"]).await {
        for line in o.lines() {
            if let Some(id) = line.split('\'').nth(2) {
                if !id.starts_with(&format!("lustre-{}-", fsname)) {
                    tracing::debug!("Found resource template from different filesystem: {} ", id);
                    continue;
                }
                if let Some(serv) = id.split('-').last() {
                    paths.push(format!(
                        "//constraints/rsc_order[@id=\"{}-client-after-{}\"]",
                        fsname, serv
                    ))
                }
            }
        }
    }
    if ids.contains(&fsname) {
        paths.push(format!(
            "//constraints/rsc_ticket[@id=\"ticket-{}-allocated-client\"]",
            fsname,
        ));
    }
    if ids.contains(&"mgs".to_string()) {
        paths.push(format!(
            "//constraints/rsc_order[@id=\"{}-client-after-mgs\"]",
            fsname
        ));
    }
    paths.push(format!("//resources/clone[@id=\"{}\"]", id));

    cibxpath("delete-all", &paths.join("|"), &["--force"]).await?;

    Ok(())
}

pub async fn create_cloned_client(
    (fsname, mountpoint): (String, String),
) -> Result<(), ImlAgentError> {
    let ids = resource_list().await?;

    if ids.contains(&format!("{}-client:0", fsname)) {
        return Ok(());
    }

    let unit = format!(
        "{}.mount",
        mountpoint
            .trim_start_matches('/')
            .replace("-", "--")
            .replace("/", "-")
    );

    let agent = ResourceAgentInfo {
        agent: ResourceAgentType {
            standard: "systemd".into(),
            provider: None,
            ocftype: unit,
        },
        id: format!("{}-client", fsname),
        args: HashMap::new(),
        ops: PacemakerOperations::new("900s".to_string(), "60s".to_string(), None),
    };

    let mut constraints = vec![];
    if ids.contains(&fsname) {
        constraints.push(ResourceConstraint::Ticket {
            id: format!("ticket-{}-allocated-client", fsname),
            rsc: agent.id.clone(),
            ticket: format!("{}-allocated", fsname),
            loss_policy: Some(LossPolicy::Stop),
        });
    }
    if ids.contains(&"mgs".to_string()) {
        constraints.push(ResourceConstraint::Order {
            id: format!("{}-client-after-mgs", fsname),
            first: "mgs".to_string(),
            first_action: Some(PacemakerActions::Start),
            then: agent.id.clone(),
            then_action: Some(PacemakerActions::Start),
            kind: Some(PacemakerKindOrScore::Score(PacemakerScore::Value(0))),
        });
    }
    if let Ok(o) = cibxpath("query", "//template[@type=\"lustre-server\"]", &["-e"]).await {
        for line in o.lines() {
            if let Some(id) = line.split('\'').nth(2) {
                if !id.starts_with(&format!("lustre-{}-", fsname)) {
                    tracing::debug!("Found resource template from different filesystem: {} ", id);
                    continue;
                }
                if let Some(serv) = id.split('-').last() {
                    constraints.push(ResourceConstraint::Order {
                        id: format!("{}-client-after-{}", fsname, serv),
                        first: id.to_string(),
                        first_action: Some(PacemakerActions::Start),
                        then: agent.id.clone(),
                        then_action: Some(PacemakerActions::Start),
                        kind: Some(PacemakerKindOrScore::Score(PacemakerScore::Value(0))),
                    });
                    continue;
                }
            }
            tracing::error!("Could not parse cibxpath query output: {}", line);
        }
    } else {
        tracing::debug!("No lustre-server templates");
    }

    create_resource(agent, true, constraints, false).await?;

    wait_resource(&format!("{}-client", fsname), false).await
}

pub async fn create_cloned_resource(
    (agent, constraints): (ResourceAgentInfo, Vec<ResourceConstraint>),
) -> Result<(), ImlAgentError> {
    let ids = resource_list().await?;

    if ids.contains(&format!("cl-{}", agent.id)) {
        return Ok(());
    }

    create_resource(agent, true, constraints, true).await
}

fn check_id(cloned: bool, id: &str, res: String) -> String {
    if cloned && id == res {
        format!("cl-{}", id)
    } else {
        res
    }
}

fn resource_xml_string(agent: &ResourceAgentInfo, cloned: bool) -> Result<String, ImlAgentError> {
    let mut res = Element::new("primitive");
    res.set_attr("id", &agent.id)
        .set_attr("class", &agent.agent.standard)
        .set_attr("type", &agent.agent.ocftype);

    if let Some(provider) = &agent.agent.provider {
        res.set_attr("provider", provider);
    }

    if !agent.args.is_empty() {
        let ia = res.append_new_child("instance_attributes");
        let iaid = format!("{}-instance_attributes", &agent.id);
        ia.set_attr("id", &iaid);
        for (k, v) in agent.args.iter() {
            xml_add_nvpair(ia, &iaid, k, v);
        }
    }

    if agent.ops.is_any_some() {
        let ops = res.append_new_child("operations");
        xml_add_op(ops, &agent.id, "start", &agent.ops.start, &None);
        xml_add_op(ops, &agent.id, "stop", &agent.ops.stop, &None);
        xml_add_op(ops, &agent.id, "monitor", &None, &agent.ops.monitor);
    }

    // add meta_attributes so resource is created in stopped state
    let ma = res.append_new_child("meta_attributes");
    let maid = format!("{}-meta_attributes", &agent.id);
    ma.set_attr("id", &maid);
    xml_add_nvpair(ma, &maid, "target-role", "Stopped");

    let rc = if cloned {
        let mut clone = Element::new("clone");
        let id = format!("cl-{}", &agent.id);
        clone.set_attr("id", id).append_child(res);
        clone.to_string()?
    } else {
        res.to_string()?
    };

    Ok(rc)
}

async fn create_resource(
    agent: ResourceAgentInfo,
    cloned: bool,
    constraints: Vec<ResourceConstraint>,
    started: bool,
) -> Result<(), ImlAgentError> {
    let xml = resource_xml_string(&agent, cloned)?;
    cibcreate("resources", &xml).await?;

    for constraint in constraints {
        let xml = {
            let con = match constraint {
                ResourceConstraint::Order {
                    id,
                    first,
                    first_action,
                    then,
                    then_action,
                    kind,
                } => {
                    let mut con = Element::new("rsc_order");
                    match kind {
                        Some(PacemakerKindOrScore::Kind(kind)) => {
                            con.set_attr("kind", kind.to_string());
                        }
                        Some(PacemakerKindOrScore::Score(score)) => {
                            con.set_attr("score", score.to_string());
                        }
                        None => (),
                    }
                    con.set_attr("id", id)
                        .set_attr("first", check_id(cloned, &agent.id, first))
                        .set_attr("then", check_id(cloned, &agent.id, then));
                    if let Some(action) = first_action {
                        con.set_attr("first-action", action.to_string());
                    }
                    if let Some(action) = then_action {
                        con.set_attr("then-action", action.to_string());
                    }
                    con
                }
                ResourceConstraint::Location {
                    id,
                    rsc,
                    node,
                    score,
                } => {
                    let mut con = Element::new("rsc_location");
                    con.set_attr("id", id)
                        .set_attr("rsc", check_id(cloned, &agent.id, rsc))
                        .set_attr("node", node)
                        .set_attr("score", score.to_string());
                    con
                }
                ResourceConstraint::Colocation {
                    id,
                    rsc,
                    with_rsc,
                    score,
                } => {
                    let mut con = Element::new("rsc_colocation");
                    con.set_attr("id", id)
                        .set_attr("rsc", check_id(cloned, &agent.id, rsc))
                        .set_attr("with-rsc", check_id(cloned, &agent.id, with_rsc))
                        .set_attr("score", score.to_string());
                    con
                }
                ResourceConstraint::Ticket {
                    id,
                    rsc,
                    ticket,
                    loss_policy,
                } => {
                    let mut con = Element::new("rsc_ticket");
                    con.set_attr("id", id)
                        .set_attr("rsc", check_id(cloned, &agent.id, rsc))
                        .set_attr("ticket", ticket);
                    if let Some(policy) = loss_policy {
                        con.set_attr("loss-policy", policy.to_string());
                    }
                    con
                }
            };

            con.to_string()?
        };
        cibcreate("constraints", &xml).await?;
    }

    // The reason the resource is ALWAYS created in the stopped state,
    // is that we need to add constraints prior to starting so it will
    // start on the correct node, or wait for other resources to
    // start.
    if started {
        cibxpath(
            "delete",
            &format!(
                "//resources/primitive[@id=\"{}\"]/meta_attributes",
                &agent.id
            ),
            NO_EXTRA,
        )
        .await?;
    }

    Ok(())
}

/// Destroy resource primitive with label and list of constraint ids
pub async fn destroy_resource(
    (label, constraints): (String, Vec<String>),
) -> Result<(), ImlAgentError> {
    let mut paths = vec![format!("//resources/primitive[@id=\"{}\"]", label)];
    paths.extend(
        constraints
            .into_iter()
            .map(|id| format!("//constraints/*[@id=\"{}\"]", id)),
    );
    cibxpath("delete-all", &paths.join("|"), &["--force"]).await?;

    Ok(())
}

async fn systemd_unit_servicestate(name: &str) -> Result<ServiceState, ImlAgentError> {
    let n = format!("{}.service", name);
    match iml_systemd::get_run_state(n).await {
        Ok(s) => Ok(ServiceState::Configured(s)),
        Err(err) => {
            tracing::debug!("Get Run State of {} failed: {:?}", name, err);
            Ok(ServiceState::Unconfigured)
        }
    }
}

async fn check_corosync() -> Result<ComponentState<bool>, ImlAgentError> {
    let mut corosync = ComponentState::<bool> {
        ..Default::default()
    };

    if file_exists("/etc/corosync/corosync.conf").await {
        let expected = r#"totem.interface.0.mcastaddr (str) = 226.94.0.1
totem.interface.1.mcastaddr (str) = 226.94.1.1
"#
        .as_bytes();
        let output = Command::new("corosync-cmapctl")
            .args(&["totem.interface.0.mcastaddr", "totem.interface.1.mcastaddr"])
            .checked_output()
            .await?;

        corosync.config = if output.stdout == expected {
            ConfigState::IML
        } else {
            ConfigState::Unknown
        };
        corosync.service = systemd_unit_servicestate("corosync").await?;
    }

    Ok(corosync)
}

async fn check_pacemaker() -> Result<ComponentState<bool>, ImlAgentError> {
    let mut pacemaker = ComponentState::<bool> {
        ..Default::default()
    };

    if file_exists("/var/lib/pacemaker/cib/cib.xml").await {
        pacemaker.service = systemd_unit_servicestate("pacemaker").await?;
        let resources = get_ha_resource_list(()).await?;
        if resources.is_empty() {
            pacemaker.config = ConfigState::Default;
        } else {
            pacemaker.config = ConfigState::Unknown;
        }
        for res in resources {
            if res.id == "st-fencing" && res.agent.ocftype == "fence_chroma" {
                pacemaker.config = ConfigState::IML;
                break;
            }
        }
    }

    Ok(pacemaker)
}

async fn check_pcs() -> Result<ComponentState<bool>, ImlAgentError> {
    let mut pcs = ComponentState::<bool> {
        ..Default::default()
    };

    if file_exists("/var/lib/pcsd/tokens").await {
        pcs.config = ConfigState::IML;
        pcs.service = systemd_unit_servicestate("pcsd").await?;
    }

    Ok(pcs)
}

pub async fn check_ha(
    _: (),
) -> Result<
    (
        ComponentState<bool>,
        ComponentState<bool>,
        ComponentState<bool>,
    ),
    ImlAgentError,
> {
    let corosync = check_corosync();
    let pacemaker = check_pacemaker();
    let pcs = check_pcs();

    try_join!(corosync, pacemaker, pcs)
}

pub async fn start_resource(resource: String) -> Result<(), ImlAgentError> {
    set_resource_role(&resource, true).await?;

    wait_resource(&resource, true).await?;
    Ok(())
}

pub async fn stop_resource(resource: String) -> Result<(), ImlAgentError> {
    set_resource_role(&resource, false).await?;

    wait_resource(&resource, false).await?;
    Ok(())
}

pub async fn move_resource((resource, dest_host): (String, String)) -> Result<(), ImlAgentError> {
    let delay_duration = Duration::new(WAIT_DELAY, 0);

    crm_resource(&["--resource", &resource, "--move", "--node", &dest_host]).await?;

    let mut counter = 0;
    let rc = loop {
        let output = crm_mon_cmd().checked_output().await?;
        let cluster = read_crm_output(&output.stdout)?;

        let res = cluster.resources.into_iter().find(|r| r.id == resource);
        if let Some(r) = res {
            if r.active_node_name.unwrap_or_else(|| "".into()) == dest_host {
                break Ok(());
            }
        }
        if counter >= WAIT_SEC {
            break Err(ImlAgentError::from(RequiredError(format!(
                "Waiting for resource {} to move to {} failed after {} sec",
                resource, dest_host, WAIT_SEC,
            ))));
        }
        counter += WAIT_DELAY;
        delay_for(delay_duration).await;
    };

    crm_resource(&["--resource", &resource, "--un-move", "--node", &dest_host]).await?;

    rc
}

#[cfg(test)]
mod tests {
    use super::{process_resource, PacemakerOperations, ResourceAgentInfo, ResourceAgentType};
    use std::collections::HashMap;

    #[test]
    fn test_ha_only_fence_chroma() {
        let testxml = include_bytes!("fixtures/crm-resource-chroma-stonith.xml");

        assert_eq!(
            process_resource(testxml).unwrap(),
            ResourceAgentInfo {
                agent: ResourceAgentType::new("stonith", None, "fence_chroma"),
                id: "st-fencing".to_string(),
                args: HashMap::new(),
                ops: PacemakerOperations::new(None, None, None),
            }
        );
    }

    #[test]
    fn test_iml() {
        let testxml = include_bytes!("fixtures/crm-resource-iml-mgs.xml");

        let r1 = ResourceAgentInfo {
            agent: ResourceAgentType::new("ocf", Some("lustre"), "Lustre"),
            id: "MGS".to_string(),
            args: vec![
                ("mountpoint", "/mnt/MGS"),
                (
                    "target",
                    "/dev/disk/by-id/scsi-36001405c20616f7b8b2492d8913a4d24",
                ),
            ]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect(),
            ops: PacemakerOperations::new(
                Some("300s".to_string()),
                Some("20s".to_string()),
                Some("300s".to_string()),
            ),
        };

        assert_eq!(process_resource(testxml).unwrap(), r1);
    }

    #[test]
    fn test_es_ost() {
        let testxml = include_bytes!("fixtures/crm-resource-es-ost.xml");

        let r1 = ResourceAgentInfo {
            agent: ResourceAgentType::new("ocf", Some("ddn"), "lustre-server"),
            id: "ost0001-es01a".to_string(),
            args: vec![
                ("lustre_resource_type", "ost"),
                ("manage_directory", "1"),
                ("device", "/dev/ddn/es01a_ost0001"),
                ("directory", "/lustre/es01a/ost0001"),
            ]
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect(),
            ops: PacemakerOperations::new(
                Some("450".to_string()),
                Some("30".to_string()),
                Some("300".to_string()),
            ),
        };

        assert_eq!(process_resource(testxml).unwrap(), r1);
    }
}
