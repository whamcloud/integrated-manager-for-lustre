// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{extract_api_id, get, get_all, get_hosts, post, wait_for_cmds, CmdWrapper},
    display_utils::{
        display_cancelled, display_error, format_error, format_success, generate_table, wrap_fut,
    },
    error::ImlManagerCliError,
};
use console::{style, Term};
use futures::future;
use iml_wire_types::{
    ApiList, Command, EndpointName, Host, HostProfile, HostProfileWrapper, ProfileTest,
    ServerProfile, TestHostJob,
};
use std::{
    collections::{BTreeSet, HashMap},
    iter,
    time::{Duration, Instant},
};
use structopt::StructOpt;
use tokio::timer::delay;

#[derive(StructOpt, Debug)]
pub struct AddHosts {
    /// The host(s) to update. Takes a hostlist expression
    #[structopt(short = "h", long = "hosts")]
    hosts: String,
    /// The profile to deploy to each host
    #[structopt(short = "p", long = "profile")]
    profile: String,
}

#[derive(Debug, StructOpt)]
pub enum ServerCommand {
    /// List all configured storage servers
    #[structopt(name = "list")]
    List,
    /// Add new servers to IML
    #[structopt(name = "add")]
    Add(AddHosts),
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

fn filter_known_hosts<'a, 'b>(
    hostlist: &'b BTreeSet<String>,
    api_hosts: &'a Vec<Host>,
) -> Vec<&'a Host> {
    api_hosts
        .iter()
        .filter(move |x| hostlist.contains(&x.fqdn) || hostlist.contains(&x.nodename))
        .collect()
}

fn is_profile_valid(x: &HostProfile, profile_name: &str) -> bool {
    let checks = x.profiles.get(profile_name);

    match checks {
        Some(xs) => xs.iter().all(|y| y.pass),
        None => false,
    }
}

async fn wait_till_agent_starts(
    hosts: &Vec<Host>,
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
            return Err(ImlManagerCliError::ApiError(
                x.error.take().unwrap().to_string(),
            ));
        };

        let profile_checks: HashMap<u32, Vec<ProfileTest>> = objects
            .iter_mut()
            .filter_map(|x| x.host_profiles.take())
            .map(|mut x| {
                x.profiles.remove(profile_name).map(|y| (x.host, y)).ok_or(
                    ImlManagerCliError::ApiError(format!(
                        "Profile {} not found for host {} while booting",
                        profile_name, x.host
                    )),
                )
            })
            .collect::<Result<HashMap<u32, Vec<ProfileTest>>, ImlManagerCliError>>()?;

        let all_passed = profile_checks
            .values()
            .all(|checks| checks.iter().all(|y| y.pass));

        if all_passed {
            return Ok(());
        } else if cnt == 120 {
            let failed_checks = profile_checks
                .iter()
                .filter(|(_, xs)| xs.iter().any(|y| !y.pass))
                .fold(vec![], |mut acc, (k, v)| {
                    let host = hosts.iter().find(|x| &x.id == k).unwrap();

                    let failed = v
                        .into_iter()
                        .filter(|y| !y.pass)
                        .map(|ProfileTest { description, .. }| description.to_string())
                        .collect::<Vec<String>>()
                        .join(",");

                    acc.push(format!(
                        "host {} has failed checks. Reasons: {}",
                        host.address, failed
                    ));

                    acc
                })
                .join("\n");

            return Err(ImlManagerCliError::ApiError(failed_checks));
        }

        delay(Instant::now() + Duration::from_millis(500)).await;
    }

    Ok(())
}

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

            let known_hosts = filter_known_hosts(&new_hosts, &api_hosts.objects);

            for known_host in known_hosts {
                display_cancelled(format!("Host {} already known to IML. Please remove first if attempting to complete deployment.", known_host.fqdn));
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
                        state && true
                    }
                });

            if !all_passed {
                return Err(ImlManagerCliError::ApiError(
                    "Preflight checks failed".into(),
                ));
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

            wait_till_agent_starts(&hosts, &profile.name).await?;

            let host_ids: Vec<_> = hosts
                .iter()
                .map(|x| ["id__in".into(), x.id.to_string()])
                .chain(iter::once(["limit".into(), "0".into()]))
                .collect();

            let ApiList { objects, .. }: ApiList<HostProfileWrapper> =
                get(HostProfile::endpoint_name(), host_ids).await?;

            tracing::debug!("Host Profiles {:?}", objects);

            let objects: Vec<_> = objects
                .into_iter()
                .filter_map(|x| x.host_profiles)
                .filter(|x| is_profile_valid(&x, &profile.name))
                .map(|x| HostProfileConfig {
                    host: x.host,
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
    };

    Ok(())
}
