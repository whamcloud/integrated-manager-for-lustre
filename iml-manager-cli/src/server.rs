// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{extract_api_id, get, get_all, get_hosts, post, put, wait_for_cmds, CmdWrapper},
    display_utils::{
        display_cancelled, display_error, format_error, format_success, generate_table, wrap_fut,
    },
    error::ImlManagerCliError,
};
use console::{style, Term};
use dialoguer::Confirmation;
use futures::future;
use iml_wire_types::{
    ApiList, AvailableAction, Command, EndpointName, Host, HostProfile, HostProfileWrapper,
    ProfileTest, ServerProfile, TestHostJob, ToCompositeId,
};
use std::{
    collections::{BTreeSet, HashMap},
    iter,
    time::Duration,
};
use structopt::StructOpt;
use tokio::time::delay_for;

#[derive(StructOpt, Debug)]
pub struct RemoveHosts {
    /// The host(s) to remove. Takes a hostlist expression
    #[structopt(short = "d", long = "delete_hosts")]
    hosts: String,
}

#[derive(StructOpt, Debug)]
pub struct AddHosts {
    /// The host(s) to update. Takes a hostlist expression
    #[structopt(short = "h", long = "hosts")]
    hosts: String,
    /// The profile to deploy to each host
    #[structopt(short = "p", long = "profile")]
    profile: String,
    /// Prompt to continue if command fails
    #[structopt(long, conflicts_with = "force")]
    prompt: bool,
    /// Always continue if command fails
    #[structopt(long)]
    force: bool,
}

#[derive(Debug, StructOpt)]
pub enum ServerCommand {
    /// List all configured storage servers
    #[structopt(name = "list")]
    List,
    /// Add new servers to IML
    #[structopt(name = "add")]
    Add(AddHosts),
    /// Remove servers from IML
    #[structopt(name = "remove")]
    Remove(RemoveHosts),
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct TestHostConfig<'a> {
    address: &'a str,
    auth_type: String,
}

#[derive(serde::Serialize, serde::Deserialize)]
struct AgentConfig<'a> {
    address: &'a str,
    auth_type: String,
    server_profile: String,
}

#[derive(serde::Serialize, serde::Deserialize)]
struct StateChange {
    state: String,
}

#[derive(serde::Serialize)]
struct HostProfileConfig<'a> {
    host: u32,
    profile: &'a str,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct CommandAndHost {
    command: Command,
    host: Host,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct CommandAndHostWrapper {
    command_and_host: Option<CommandAndHost>,
    error: Option<String>,
    traceback: Option<String>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct HostProfileCmdWrapper {
    commands: Vec<Command>,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct Objects<T> {
    objects: Vec<T>,
}

/// Given an expanded hostlist and a list of API host objects
/// returns a tuple of hosts that match a hostlist item, and the remaining hostlist items
/// that did not match anything.
fn filter_known_hosts<'a>(
    hostlist: BTreeSet<String>,
    api_hosts: &'a [Host],
) -> (Vec<&'a Host>, BTreeSet<String>) {
    hostlist
        .into_iter()
        .map(
            |x| match api_hosts.iter().find(|y| y.fqdn == x || y.nodename == x) {
                Some(y) => (Some(y), None),
                None => (None, Some(x)),
            },
        )
        .fold((vec![], BTreeSet::new()), |(mut xs, mut ys), x| {
            match x {
                (Some(x), None) => {
                    xs.push(x);
                }
                (None, Some(y)) => {
                    ys.insert(y);
                }
                _ => {}
            }

            (xs, ys)
        })
}

fn can_continue(config: &AddHosts) -> bool {
    config.force || (config.prompt && get_confirm())
}

fn get_confirm() -> bool {
    Confirmation::new()
        .with_text("Continue deployment?")
        .default(true)
        .show_default(true)
        .interact()
        .unwrap_or(false)
}

async fn wait_till_agent_starts(
    hosts: &[Host],
    profile_name: &str,
) -> Result<(), ImlManagerCliError> {
    let host_ids: Vec<_> = hosts
        .iter()
        .map(|x| ["id__in".into(), x.id.to_string()])
        .chain(iter::once(["limit".into(), "0".into()]))
        .collect();

    let upper: u32 = 120;

    for cnt in 1..=upper {
        let ApiList { mut objects, .. }: ApiList<HostProfileWrapper> =
            get(HostProfile::endpoint_name(), &host_ids).await?;

        tracing::debug!("Host Profiles {:?}", objects);

        if let Some(x) = objects.iter_mut().find(|x| x.error.is_some()) {
            return Err(ImlManagerCliError::ApiError(x.error.take().unwrap()));
        };

        let profile_checks: HashMap<u32, Vec<ProfileTest>> = objects
            .iter_mut()
            .filter_map(|x| x.host_profiles.take())
            .map(|mut x| {
                x.profiles
                    .remove(profile_name)
                    .map(|y| (x.host, y))
                    .ok_or_else(|| {
                        ImlManagerCliError::ApiError(format!(
                            "Profile {} not found for host {} while booting",
                            profile_name, x.host
                        ))
                    })
            })
            .collect::<Result<HashMap<u32, Vec<ProfileTest>>, ImlManagerCliError>>()?;

        let waiting_for_agent: Vec<_> = profile_checks
            .iter()
            .filter(|(_, checks)| {
                checks
                    .iter()
                    .any(|y| y.error == "Result unavailable while host agent starts")
            })
            .map(|(k, _)| hosts.iter().find(|x| &x.id == k).unwrap())
            .map(|x| {
                format!(
                    "No contact with IML agent on {} for 60s (after restart)",
                    x.address
                )
            })
            .collect();

        if waiting_for_agent.is_empty() {
            return Ok(());
        }

        if cnt == upper {
            return Err(ImlManagerCliError::ApiError(waiting_for_agent.join("\n")));
        }

        delay_for(Duration::from_millis(500)).await;
    }

    Ok(())
}

#[allow(clippy::cognitive_complexity)]
pub async fn server_cli(command: ServerCommand) -> Result<(), ImlManagerCliError> {
    match command {
        ServerCommand::List => {
            let hosts: ApiList<Host> = wrap_fut("Fetching hosts...", get_hosts()).await?;

            tracing::debug!("Hosts: {:?}", hosts);

            let table = generate_table(
                &["Id", "FQDN", "State", "Nids"],
                hosts.objects.into_iter().map(|h| {
                    vec![
                        h.id.to_string(),
                        h.fqdn,
                        h.state,
                        h.nids.unwrap_or_else(|| vec![]).join(" "),
                    ]
                }),
            );

            table.printstd();
        }
        ServerCommand::Add(config) => {
            let term = Term::stdout();

            let new_hosts = hostlist_parser::parse(&config.hosts)?;

            tracing::debug!("Parsed hosts {:?}", new_hosts);

            let (profiles, api_hosts): (ApiList<ServerProfile>, ApiList<Host>) =
                future::try_join(get_all(), get_all()).await?;

            let profile_opt = profiles
                .objects
                .into_iter()
                .filter(|x| x.user_selectable)
                .find(|x| x.name == config.profile);

            let profile = match profile_opt {
                Some(p) => p,
                None => {
                    display_error(format!("Unknown profile {}", config.profile));

                    return Ok(());
                }
            };

            let (known_hosts, new_hosts) = filter_known_hosts(new_hosts, &api_hosts.objects);

            for known_host in known_hosts {
                display_cancelled(format!("Host {} already known to IML. Please remove first if attempting to complete deployment.", known_host.fqdn));
            }

            if new_hosts.is_empty() {
                return Ok(());
            }

            let objects = new_hosts
                .iter()
                .map(|address| TestHostConfig {
                    address,
                    auth_type: "existing_keys_choice".into(),
                })
                .collect();

            let Objects { objects } = post("test_host", Objects { objects })
                .await?
                .error_for_status()?
                .json()
                .await
                .map_err(iml_manager_client::ImlManagerClientError::Reqwest)?;

            let cmds = objects
                .into_iter()
                .map(|CmdWrapper { command }| command)
                .collect();

            tracing::debug!("cmds {:?}", cmds);

            term.write_line(&format!("{} preflight checks...", style("Running").green()))?;

            let cmds = wait_for_cmds(cmds).await?;

            let jobs: Vec<_> = cmds
                .into_iter()
                .flat_map(|cmd| cmd.jobs)
                .filter_map(|job| extract_api_id(&job).map(|x| x.to_string()))
                .map(|x| ["id__in".into(), x])
                .chain(iter::once(["limit".into(), "0".into()]))
                .collect();

            let jobs: ApiList<TestHostJob> = get(TestHostJob::endpoint_name(), jobs).await?;

            tracing::debug!("jobs {:?}", jobs);

            let all_passed = jobs
                .objects
                .into_iter()
                .flat_map(|x| x.step_results.into_iter().map(|(_, b)| b))
                .fold(true, |state, check| {
                    if !check.valid {
                        display_error(format!(
                            "Host {} has failed pre-flight checks.",
                            check.address,
                        ));

                        generate_table(
                            &["Check", "Passed"],
                            check.status.iter().map(|x| {
                                let v = if x.value {
                                    format_success("Pass")
                                } else {
                                    format_error("Fail")
                                };

                                vec![x.name.clone(), v]
                            }),
                        );

                        false
                    } else {
                        state
                    }
                });

            if !all_passed {
                let error_msg = "Preflight checks failed";

                display_error(&error_msg);

                if !can_continue(&config) {
                    return Err(ImlManagerCliError::ApiError(error_msg.into()));
                }
            }

            let objects = new_hosts
                .iter()
                .map(|address| AgentConfig {
                    address,
                    auth_type: "existing_keys_choice".into(),
                    server_profile: "/api/server_profile/default/".into(),
                })
                .collect();

            let Objects { objects }: Objects<CommandAndHostWrapper> =
                post(Host::endpoint_name(), Objects { objects })
                    .await?
                    .json()
                    .await
                    .map_err(iml_manager_client::ImlManagerClientError::Reqwest)?;

            tracing::debug!("command and hosts {:?}", objects);

            let (commands, hosts): (Vec<_>, Vec<_>) = objects
                .into_iter()
                .filter_map(|x| x.command_and_host)
                .map(|x| (x.command, x.host))
                .unzip();

            term.write_line(&format!("{} agents...", style("Deploying").green()))?;

            wait_for_cmds(commands).await?;

            wrap_fut(
                "Waiting for agents to restart...",
                wait_till_agent_starts(&hosts, &profile.name),
            )
            .await?;

            let host_ids: Vec<_> = hosts
                .iter()
                .map(|x| ["id__in".into(), x.id.to_string()])
                .chain(iter::once(["limit".into(), "0".into()]))
                .collect();

            let ApiList { objects, .. }: ApiList<HostProfileWrapper> =
                get(HostProfile::endpoint_name(), host_ids).await?;

            tracing::debug!("Host Profiles {:?}", objects);

            let objects: Vec<(u32, _)> = objects
                .into_iter()
                .filter_map(|x| x.host_profiles)
                .filter_map(|mut x| x.profiles.remove(&profile.name).map(|p| (x.host, p)))
                .collect();

            let invalid: Vec<_> = objects
                .iter()
                .map(|(k, tests)| (k, tests.iter().filter(|y| !y.pass).collect::<Vec<_>>()))
                .filter(|(_, tests)| !tests.is_empty())
                .collect();

            if !invalid.is_empty() {
                display_error(format!("Profile {} is invalid:\n\n", profile.name));

                for (host_id, failed_tests) in invalid {
                    let host = hosts.iter().find(|x| &x.id == host_id).unwrap();

                    display_error(format!("Host {}\n", host.address));

                    let table = generate_table(
                        &["Description", "Test", "Error"],
                        failed_tests
                            .into_iter()
                            .map(|x| vec![&x.description, &x.test, &x.error]),
                    );

                    table.printstd();

                    term.write_line("\n\n")?;
                }

                if !can_continue(&config) {
                    return Err(ImlManagerCliError::ApiError(
                        "Did not deploy profile.".into(),
                    ));
                }
            }

            let objects = objects
                .into_iter()
                .map(|(host, _)| HostProfileConfig {
                    host,
                    profile: &profile.name,
                })
                .collect();

            let Objects { objects } = post(HostProfile::endpoint_name(), Objects { objects })
                .await?
                .json()
                .await
                .map_err(iml_manager_client::ImlManagerClientError::Reqwest)?;

            tracing::debug!("Host Profile resp {:?}", objects);

            let cmds = objects
                .into_iter()
                .flat_map(|HostProfileCmdWrapper { commands }| commands)
                .collect();

            term.write_line(&format!("{} host profiles...", style("Setting").green()))?;

            wait_for_cmds(cmds).await?;
        }
        ServerCommand::Remove(config) => {
            let remove_hosts = hostlist_parser::parse(&config.hosts)?;

            tracing::debug!("Parsed hosts {:?}", remove_hosts);

            let api_hosts = wrap_fut("Fetching hosts...", get_hosts()).await?;

            let (hosts, unknown_names) = filter_known_hosts(remove_hosts, &api_hosts.objects);

            for unknown_name in unknown_names {
                display_cancelled(format!(
                    "Host {} unknown to IML; it will not be removed.",
                    unknown_name
                ));
            }

            let xs: Vec<_> = hosts
                .iter()
                .map(|x| x.composite_id())
                .map(|x| ("composite_ids", x.to_string()))
                .chain(std::iter::once(("limit", "0".into())))
                .collect();

            let actions: ApiList<AvailableAction> =
                get(AvailableAction::endpoint_name(), &xs).await?;

            let removable_ids = actions
                .objects
                .into_iter()
                .fold(BTreeSet::new(), |mut xs, x| {
                    if x.verb == "Remove" {
                        xs.insert(x.composite_id);
                    }

                    xs
                });

            let (removable, not_removable): (Vec<_>, Vec<_>) = hosts
                .into_iter()
                .partition(|x| removable_ids.contains(&x.composite_id().to_string()));

            for x in not_removable {
                display_cancelled(format!("Host {} is unable to be removed.", x.fqdn));
            }

            if removable.is_empty() {
                return Ok(());
            }

            let xs: Vec<_> = removable
                .into_iter()
                .map(|x| async move {
                    let r = put(
                        &x.resource_uri,
                        StateChange {
                            state: "removed".into(),
                        },
                    )
                    .await?
                    .error_for_status()?;

                    let CmdWrapper { command } = r.json().await?;

                    Ok::<_, ImlManagerCliError>(command)
                })
                .collect();

            let commands: Vec<Command> =
                wrap_fut("Removing Servers...", future::try_join_all(xs)).await?;

            wait_for_cmds(commands).await?;
        }
    };

    Ok(())
}
