// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{
        get, get_all, get_hosts, post, put, wait_for_cmds, wait_for_cmds_success, SendCmd, SendJob,
    },
    display_utils::{
        display_cancelled, display_error, format_error, format_success, generate_table, wrap_fut,
        DisplayType, IntoDisplayType as _,
    },
    error::EmfManagerCliError,
    parse_hosts, profile,
};
use console::{style, Term};
use dialoguer::Confirm;
use emf_wire_types::{
    ApiList, AvailableAction, CmdWrapper, Command, EndpointName, Host, ProfileTest, ServerProfile,
    TestHostJob, ToCompositeId,
};
use futures::future;
use std::{
    collections::BTreeSet,
    io::{Error, ErrorKind},
    iter,
};
use structopt::StructOpt;
use tokio::io::{stdin, AsyncReadExt};

#[derive(StructOpt, Debug)]
pub struct AddHosts {
    /// The profile to deploy to each host
    #[structopt(short = "p", long = "profile")]
    profile: String,
    /// Prompt to continue if command fails
    #[structopt(long, conflicts_with = "force")]
    prompt: bool,
    /// Always continue if command fails
    #[structopt(long)]
    force: bool,

    /// Authentication Type (shared, password, private)
    /// for "private" key is read from stdin
    #[structopt(name = "auth", long, short, default_value = "shared")]
    auth: String,

    /// Password for "password" or password for "private" key
    #[structopt(long, short = "P", required_if("auth", "password"))]
    password: Option<String>,

    /// Hostlist expressions, e. g. mds[1,2].local
    #[structopt(required = true, min_values = 1)]
    hosts: Vec<String>,
}

#[derive(Debug, StructOpt)]
pub enum ServerCommand {
    /// List all configured storage servers (default)
    #[structopt(name = "list")]
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
    /// Add new servers
    #[structopt(name = "add")]
    Add(AddHosts),
    /// Remove servers
    #[structopt(name = "remove")]
    Remove {
        /// Hostlist expressions, e. g. mds[1,2].local
        #[structopt(required = true, min_values = 1)]
        hosts: Vec<String>,
    },
    /// Remove servers from DB, but leave agents in place.
    #[structopt(name = "force-remove")]
    ForceRemove {
        /// Hostlist expressions, e. g. mds[1,2].local
        #[structopt(required = true, min_values = 1)]
        hosts: Vec<String>,
    },
    /// Work with server profiles
    #[structopt(name = "profile")]
    Profile {
        #[structopt(subcommand)]
        cmd: Option<profile::Cmd>,
    },
}

#[derive(Debug)]
pub enum AuthType {
    Shared,
    Password(String),
    PrivateKey(String),
}

impl From<&AuthType> for String {
    fn from(auth: &AuthType) -> Self {
        match auth {
            AuthType::Shared => "existing_keys_choice".into(),
            AuthType::Password(_) => "id_password_root".into(),
            AuthType::PrivateKey(_) => "private_key_choice".into(),
        }
    }
}

#[derive(Debug, serde::Serialize, serde::Deserialize, Default)]
struct TestHostConfig<'a> {
    address: &'a str,
    auth_type: String,
    // For auth_type == "id_password_root"
    root_password: Option<String>,
    // For auth_type == "private_key_choice"
    private_key: Option<String>,
}

impl<'a> TestHostConfig<'a> {
    fn new(address: &'a str, auth: &AuthType) -> Self {
        Self {
            address,
            auth_type: auth.into(),
            root_password: {
                if let AuthType::Password(pass) = auth {
                    Some(pass.clone())
                } else {
                    None
                }
            },
            private_key: {
                if let AuthType::PrivateKey(key) = auth {
                    Some(key.clone())
                } else {
                    None
                }
            },
        }
    }
}

#[derive(serde::Serialize, serde::Deserialize)]
struct AgentConfig<'a> {
    server_profile: &'a str,
    #[serde(flatten, borrow)]
    info: TestHostConfig<'a>,
}

#[derive(serde::Serialize, serde::Deserialize)]
struct StateChange {
    state: String,
}

#[derive(serde::Serialize)]
struct HostProfileConfig<'a> {
    host: i32,
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
    Confirm::new()
        .with_prompt("Continue deployment?")
        .default(true)
        .show_default(true)
        .interact()
        .unwrap_or(false)
}

async fn list_server(display_type: DisplayType) -> Result<(), EmfManagerCliError> {
    let hosts: ApiList<Host> = wrap_fut("Fetching hosts...", get_hosts()).await?;

    let term = Term::stdout();

    tracing::debug!("Hosts: {:?}", hosts);

    let x = hosts.objects.into_display_type(display_type);

    term.write_line(&x).unwrap();

    Ok(())
}

fn get_profile_by_name<'a>(xs: &'a [ServerProfile], name: &str) -> Option<&'a ServerProfile> {
    let profile_opt = xs
        .iter()
        .filter(|x| x.user_selectable)
        .find(|x| x.name == name);

    if profile_opt.is_none() {
        display_error(format!("Unknown profile {}", name));
    }

    profile_opt
}

fn show_known_host_messages<'a, I>(known_hosts: I)
where
    I: IntoIterator<Item = &'a Host>,
{
    for known_host in known_hosts {
        display_cancelled(format!(
            "Host {} already known. Please remove first if attempting to complete deployment.",
            known_host.fqdn
        ));
    }
}

fn get_test_host_configs<'a>(
    new_hosts: &'a BTreeSet<String>,
    auth: &AuthType,
) -> Vec<TestHostConfig<'a>> {
    new_hosts
        .iter()
        .map(|address| TestHostConfig::new(address, auth))
        .collect()
}

async fn post_test_host<'a>(
    objects: Vec<TestHostConfig<'a>>,
) -> Result<Objects<CmdWrapper>, EmfManagerCliError> {
    Ok(post("test_host", Objects { objects })
        .await?
        .error_for_status()?
        .json::<Objects<CmdWrapper>>()
        .await
        .map_err(emf_manager_client::EmfManagerClientError::Reqwest)?)
}

fn get_commands_from_objects<I>(objects: I) -> Vec<Command>
where
    I: IntoIterator<Item = CmdWrapper>,
{
    objects
        .into_iter()
        .map(|CmdWrapper { command }| command)
        .collect()
}

fn get_jobs_from_commands<I>(cmds: I) -> Vec<[String; 2]>
where
    I: IntoIterator<Item = Command>,
{
    cmds.into_iter()
        .flat_map(|cmd| cmd.jobs)
        .filter_map(|job| emf_api_utils::extract_id(&job).map(|x| x.to_string()))
        .map(|x| ["id__in".into(), x])
        .chain(iter::once(["limit".into(), "0".into()]))
        .collect()
}

fn all_jobs_passed(jobs: ApiList<TestHostJob>, profile: &ServerProfile, term: &Term) -> bool {
    jobs.objects
        .into_iter()
        .flat_map(|x| x.step_results.into_iter().map(|(_, b)| b))
        .fold(true, |state, check| {
            if !check.valid {
                display_error(format!(
                    "Host {} has failed pre-flight checks.",
                    check.address,
                ));

                let table = generate_table(
                    &["Check", "Passed"],
                    check.status.into_iter().map(|x| {
                        let v = if x.value {
                            format_success("Pass")
                        } else {
                            format_error("Fail")
                        };

                        vec![x.name, v]
                    }),
                );

                term.write_line("\n").unwrap();

                table.printstd();

                term.write_line("\n").unwrap();

                false
            } else if let Some(xs) = check.profiles.get(&profile.name) {
                let failed_tests: Vec<_> = xs.iter().filter(|y| !y.pass).collect();

                handle_invalid_profile_tests(term, &profile, &failed_tests);

                state && failed_tests.is_empty()
            } else {
                state
            }
        })
}

fn handle_test_host_failure(all_passed: bool, config: &AddHosts) -> Result<(), EmfManagerCliError> {
    if !all_passed {
        let error_msg = "Preflight checks failed";

        display_error(&error_msg);

        if !can_continue(config) {
            return Err(EmfManagerCliError::ApiError(error_msg.into()));
        }
    }

    Ok(())
}

fn get_agent_config_objects<'a>(
    new_hosts: &'a BTreeSet<String>,
    server_profile: &'a ServerProfile,
    auth: &AuthType,
) -> Vec<AgentConfig<'a>> {
    new_hosts
        .iter()
        .map(|address| AgentConfig {
            info: TestHostConfig::new(&address, &auth),
            server_profile: &server_profile.resource_uri,
        })
        .collect()
}

async fn post_command_to_host<'a>(
    objects: Vec<AgentConfig<'a>>,
) -> Result<Objects<CommandAndHostWrapper>, EmfManagerCliError> {
    Ok(post(Host::endpoint_name(), Objects { objects })
        .await?
        .json()
        .await
        .map_err(emf_manager_client::EmfManagerClientError::Reqwest)?)
}

fn get_commands_and_hosts_from_objects<I>(objects: I) -> (Vec<Command>, Vec<Host>)
where
    I: IntoIterator<Item = CommandAndHostWrapper>,
{
    objects
        .into_iter()
        .filter_map(|x| x.command_and_host)
        .map(|x| (x.command, x.host))
        .unzip()
}

fn handle_invalid_profile_tests(
    term: &Term,
    profile: &ServerProfile,
    failed_tests: &[&ProfileTest],
) {
    if !failed_tests.is_empty() {
        display_error(format!("Profile {} is invalid:\n\n", profile.name));

        let table = generate_table(
            &["Description", "Test", "Error"],
            failed_tests
                .iter()
                .map(|x| vec![&x.description, &x.test, &x.error]),
        );

        table.printstd();

        term.write_line("\n\n").unwrap();
    }
}

async fn process_addhosts(
    config: &AddHosts,
    api_hosts: &[Host],
    new_hosts: BTreeSet<String>,
) -> Result<(BTreeSet<String>, AuthType), EmfManagerCliError> {
    let (known_hosts, new_hosts) = filter_known_hosts(new_hosts, &api_hosts);

    show_known_host_messages(known_hosts);

    let auth = match config.auth.as_str() {
        "shared" => AuthType::Shared,
        "private" => {
            let mut buf: Vec<u8> = Vec::new();
            stdin().read_to_end(&mut buf).await?;
            AuthType::PrivateKey(String::from_utf8_lossy(&buf).to_string())
        }
        "password" => AuthType::Password(config.password.clone().unwrap_or_default()),
        bad => {
            return Err(not_found_err(format!("{} not a valid auth type", bad)));
        }
    };

    Ok((new_hosts, auth))
}

async fn get_test_host_commands_and_jobs(
    term: &Term,
    new_hosts: &BTreeSet<String>,
    auth: &AuthType,
    profile: &ServerProfile,
) -> Result<bool, EmfManagerCliError> {
    let objects = get_test_host_configs(&new_hosts, auth);

    let Objects { objects } = post_test_host(objects).await?;

    let cmds = get_commands_from_objects(objects);

    tracing::debug!("cmds {:?}", cmds);

    term.write_line(&format!("{} preflight checks...", style("Running").green()))?;

    let cmds = wait_for_cmds(&cmds).await?;

    let jobs = get_jobs_from_commands(cmds);

    let jobs: ApiList<TestHostJob> = get(TestHostJob::endpoint_name(), jobs).await?;

    tracing::debug!("jobs {:?}", jobs);

    let all_passed = all_jobs_passed(jobs, profile, term);

    Ok(all_passed)
}

async fn deploy_agents(
    term: &Term,
    new_hosts: &BTreeSet<String>,
    server_profile: &ServerProfile,
    auth: &AuthType,
) -> Result<(), EmfManagerCliError> {
    let objects = get_agent_config_objects(new_hosts, server_profile, auth);

    let Objects { objects }: Objects<CommandAndHostWrapper> = post_command_to_host(objects).await?;

    tracing::debug!("command and hosts {:?}", objects);

    let (commands, _): (Vec<_>, Vec<_>) = get_commands_and_hosts_from_objects(objects);

    term.write_line(&format!("{} agents...", style("Deploying").green()))?;

    wait_for_cmds_success(&commands).await?;

    Ok(())
}

async fn add_server(config: AddHosts) -> Result<(), EmfManagerCliError> {
    let term = Term::stdout();

    let new_hosts = parse_hosts(&config.hosts)?;

    tracing::debug!("Parsed hosts {:?}", new_hosts);

    let (profiles, api_hosts): (ApiList<ServerProfile>, ApiList<Host>) =
        future::try_join(get_all(), get_all()).await?;

    let server_profile = get_profile_by_name(&profiles.objects, &config.profile)
        .ok_or_else(|| not_found_err(format!("{} profile not found.", &config.profile)))?;

    let (new_hosts, auth) = process_addhosts(&config, &api_hosts.objects, new_hosts).await?;

    if new_hosts.is_empty() {
        return Err(not_found_err("No new hosts found"));
    }

    tracing::debug!("AUTH: {:?}", auth);

    let all_passed =
        get_test_host_commands_and_jobs(&term, &new_hosts, &auth, &server_profile).await?;

    handle_test_host_failure(all_passed, &config)?;

    deploy_agents(&term, &new_hosts, &server_profile, &auth).await?;

    Ok(())
}

pub async fn server_cli(command: Option<ServerCommand>) -> Result<(), EmfManagerCliError> {
    server(command.unwrap_or(ServerCommand::List {
        display_type: DisplayType::Tabular,
    }))
    .await
}

async fn server(command: ServerCommand) -> Result<(), EmfManagerCliError> {
    match command {
        ServerCommand::List { display_type } => list_server(display_type).await?,
        ServerCommand::Add(config) => add_server(config).await?,
        ServerCommand::ForceRemove { hosts } => {
            let remove_hosts = parse_hosts(&hosts)?;

            tracing::debug!("Parsed hosts {:?}", remove_hosts);

            let api_hosts = wrap_fut("Fetching hosts...", get_hosts()).await?;

            let (hosts, unknown_names) = filter_known_hosts(remove_hosts, &api_hosts.objects);

            for unknown_name in unknown_names {
                display_cancelled(format!(
                    "Host {} unknown; it will not be force removed.",
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

            let removable: Vec<_> = actions
                .objects
                .into_iter()
                .filter(|x| x.verb == "Force Remove")
                .collect();

            if removable.is_empty() {
                return Ok(());
            }

            hosts
                .into_iter()
                .filter(|x| {
                    removable
                        .iter()
                        .find(|y| y.composite_id == x.composite_id())
                        .is_none()
                })
                .for_each(|x| {
                    display_cancelled(format!("Host {} is unable to be force removed.", x.fqdn));
                });

            let jobs: Vec<_> = removable
                .iter()
                .map(|x| SendJob {
                    class_name: x.class_name.clone().unwrap(),
                    args: &x.args,
                })
                .collect();

            let cmd = post(
                Command::endpoint_name(),
                SendCmd {
                    jobs,
                    message: "Force Remove hosts".to_string(),
                },
            )
            .await?
            .error_for_status()?;

            let command: Command = wrap_fut("Removing Hosts...", cmd.json()).await?;

            wait_for_cmds_success(&[command]).await?;
        }
        ServerCommand::Remove { hosts } => {
            let remove_hosts = parse_hosts(&hosts)?;

            tracing::debug!("Parsed hosts {:?}", remove_hosts);

            let api_hosts = wrap_fut("Fetching hosts...", get_hosts()).await?;

            let (hosts, unknown_names) = filter_known_hosts(remove_hosts, &api_hosts.objects);

            for unknown_name in unknown_names {
                display_cancelled(format!(
                    "Host {} in unknown and cannot be removed.",
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
                .partition(|x| removable_ids.contains(&x.composite_id()));

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

                    Ok::<_, EmfManagerCliError>(command)
                })
                .collect();

            let commands: Vec<Command> =
                wrap_fut("Removing Servers...", future::try_join_all(xs)).await?;

            wait_for_cmds_success(&commands).await?;
        }
        ServerCommand::Profile { cmd } => profile::cmd(cmd).await?,
    };

    Ok(())
}

fn not_found_err(x: impl Into<String>) -> EmfManagerCliError {
    Error::new(ErrorKind::NotFound, x.into()).into()
}
