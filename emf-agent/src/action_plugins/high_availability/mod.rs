// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub(crate) mod corosync_conf;
pub(crate) mod pacemaker;

use crate::{
    agent_error::{EmfAgentError, RequiredError},
    high_availability::{
        cibcreate, cibxpath, crm_mon_cmd, crm_resource, read_crm_output, set_resource_role,
    },
};
use elementtree::Element;
use emf_cmd::{CheckedCommandExt, Command};
use emf_fs::file_exists;
use emf_wire_types::{
    pacemaker::{
        AttributeActions, Constraint, Id, KindOrScore, LossPolicy, Operations, Primitive, Resource,
        ResourceAgent, Score,
    },
    ComponentState, ConfigState, ServiceState,
};
use futures::{future::try_join_all, try_join};
use std::{convert::TryFrom, time::Duration};
use tokio::time::sleep;

pub use crate::high_availability::{crm_attribute, pcs};

const NO_EXTRA: Vec<String> = vec![];

const WAIT_SEC: u64 = 300;
const WAIT_DELAY: u64 = 2;

async fn wait_resource(resource: &str, running: bool) -> Result<(), EmfAgentError> {
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
        sleep(delay_duration).await;
    }
    Err(EmfAgentError::from(RequiredError(format!(
        "Waiting for resource {} of {} failed after {} sec",
        if running { "start" } else { "stop" },
        resource,
        sec_to_wait,
    ))))
}

fn process_resource(output: &[u8]) -> Result<Resource, EmfAgentError> {
    let element = Element::from_reader(output)?;

    Ok(Resource::try_from(&element)?)
}

async fn resource_list() -> Result<Vec<String>, EmfAgentError> {
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

pub async fn get_ha_resource_list(_: ()) -> Result<Vec<Resource>, EmfAgentError> {
    let xs = resource_list().await?.into_iter().map(|res| async move {
        let output = crm_resource(&["--query-xml", "--resource", &res]).await?;
        if let Some(xml) = output.split("xml:").last() {
            process_resource(xml.as_bytes())
        } else {
            Err(EmfAgentError::MarkerNotFound)
        }
    });
    try_join_all(xs).await
}

pub async fn create_single_resource(
    (agent, constraints): (Resource, Vec<Constraint>),
) -> Result<(), EmfAgentError> {
    let ids = resource_list().await?;

    if ids.contains(&agent.id()) {
        return Ok(());
    }

    create_resource(agent, constraints, true).await
}

pub async fn destroy_cloned_client(fsname: String) -> Result<(), EmfAgentError> {
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
) -> Result<(), EmfAgentError> {
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

    let agent = Primitive::new(
        format!("{}-client", fsname),
        ResourceAgent::new("systemd", None, unit.as_str()),
        Operations::new("900s".to_string(), "60s".to_string(), None),
    );

    let mut constraints = vec![];
    if ids.contains(&fsname) {
        constraints.push(Constraint::Ticket {
            id: format!("ticket-{}-allocated-client", fsname),
            rsc: agent.id.clone(),
            ticket: format!("{}-allocated", fsname),
            loss_policy: Some(LossPolicy::Stop),
        });
    }
    if ids.contains(&"mgs".to_string()) {
        constraints.push(Constraint::Order {
            id: format!("{}-client-after-mgs", fsname),
            first: "mgs".to_string(),
            first_action: Some(AttributeActions::Start),
            then: agent.id.clone(),
            then_action: Some(AttributeActions::Start),
            kind: Some(KindOrScore::Score(Score::Value(0))),
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
                    constraints.push(Constraint::Order {
                        id: format!("{}-client-after-{}", fsname, serv),
                        first: id.to_string(),
                        first_action: Some(AttributeActions::Start),
                        then: agent.id.clone(),
                        then_action: Some(AttributeActions::Start),
                        kind: Some(KindOrScore::Score(Score::Value(0))),
                    });
                    continue;
                }
            }
            tracing::error!("Could not parse cibxpath query output: {}", line);
        }
    } else {
        tracing::debug!("No lustre-server templates");
    }

    create_resource(agent.into(), constraints, false).await?;

    wait_resource(&format!("{}-client", fsname), false).await
}

fn to_xml_string(x: impl Into<Element>) -> Result<String, EmfAgentError> {
    let e: Element = x.into();

    Ok(e.to_string()?)
}

async fn create_resource(
    resource: Resource,
    constraints: Vec<Constraint>,
    started: bool,
) -> Result<(), EmfAgentError> {
    let mut r2 = resource.clone();
    r2.set_target_role("Stopped");

    let xml = to_xml_string(&r2)?;
    cibcreate("resources", &xml).await?;

    for constraint in constraints {
        let xml = to_xml_string(&constraint)?;
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
                r#"//resources/[@id="{}"]/meta_attributes/nvpair[@name="target-role"]"#,
                &resource.id()
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
) -> Result<(), EmfAgentError> {
    let mut paths = vec![format!("//resources/*[@id=\"{}\"]", label)];
    paths.extend(
        constraints
            .into_iter()
            .map(|id| format!("//constraints/*[@id=\"{}\"]", id)),
    );
    cibxpath("delete-all", &paths.join("|"), &["--force"]).await?;

    Ok(())
}

async fn systemd_unit_servicestate(name: &str) -> Result<ServiceState, EmfAgentError> {
    let n = format!("{}.service", name);
    match emf_systemd::get_run_state(n).await {
        Ok(s) => Ok(ServiceState::Configured(s)),
        Err(err) => {
            tracing::debug!("Get Run State of {} failed: {:?}", name, err);
            Ok(ServiceState::Unconfigured)
        }
    }
}

async fn check_corosync() -> Result<ComponentState<bool>, EmfAgentError> {
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
            .kill_on_drop(true)
            .checked_output()
            .await?;

        corosync.config = if output.stdout == expected {
            ConfigState::EMF
        } else {
            ConfigState::Unknown
        };
        corosync.service = systemd_unit_servicestate("corosync").await?;
    }

    Ok(corosync)
}

async fn check_pacemaker() -> Result<ComponentState<bool>, EmfAgentError> {
    let mut pacemaker = ComponentState::<bool> {
        ..Default::default()
    };

    if file_exists("/var/lib/pacemaker/cib/cib.xml").await {
        pacemaker.service = systemd_unit_servicestate("pacemaker").await?;
        let resources = resource_list().await?;
        if resources.is_empty() {
            pacemaker.config = ConfigState::Default;
        } else if resources.contains(&"sfa-home-vd:0".to_string()) {
            pacemaker.config = ConfigState::EMF;
        } else {
            pacemaker.config = ConfigState::Unknown;
        }
    }

    Ok(pacemaker)
}

async fn check_pcs() -> Result<ComponentState<bool>, EmfAgentError> {
    let mut pcs = ComponentState::<bool> {
        ..Default::default()
    };

    if file_exists("/var/lib/pcsd/tokens").await {
        pcs.config = ConfigState::EMF;
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
    EmfAgentError,
> {
    let corosync = check_corosync();
    let pacemaker = check_pacemaker();
    let pcs = check_pcs();

    try_join!(corosync, pacemaker, pcs)
}

pub async fn start_resource(resource: String) -> Result<(), EmfAgentError> {
    set_resource_role(&resource, true).await?;

    wait_resource(&resource, true).await?;
    Ok(())
}

pub async fn stop_resource(resource: String) -> Result<(), EmfAgentError> {
    set_resource_role(&resource, false).await?;

    wait_resource(&resource, false).await?;
    Ok(())
}

pub async fn move_resource((resource, dest_host): (String, String)) -> Result<(), EmfAgentError> {
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
            break Err(EmfAgentError::from(RequiredError(format!(
                "Waiting for resource {} to move to {} failed after {} sec",
                resource, dest_host, WAIT_SEC,
            ))));
        }
        counter += WAIT_DELAY;
        sleep(delay_duration).await;
    };

    crm_resource(&["--resource", &resource, "--un-move", "--node", &dest_host]).await?;

    rc
}
