// Copyright (c) 2020 DDN. All rights reserved.
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
    error::ImlManagerCliError,
    profile,
};
use console::{style, Term};
use dialoguer::Confirm;
use futures::future;
use iml_wire_types::{
    ApiList, AvailableAction, CmdWrapper, Command, EndpointName, Host, HostProfile,
    HostProfileWrapper, ProfileTest, ServerProfile, TestHostJob, ToCompositeId,
};
use std::{
    collections::{BTreeSet, HashMap},
    io::{Error, ErrorKind},
    iter,
    time::Duration,
};
use structopt::StructOpt;
use tokio::{
    io::{stdin, AsyncReadExt},
    time::delay_for,
};

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

    /// Authentication Type (shared, password, private)
    /// for "private" key is read from stdin
    #[structopt(name = "auth", long, short, default_value = "shared")]
    auth: String,

    /// Password for "password" or password for "private" key
    #[structopt(long, short = "P", required_if("auth", "password"))]
    password: Option<String>,
}

#[derive(Debug, StructOpt)]
pub enum ServerCommand {
    /// List all configured storage servers
    #[structopt(name = "list")]
    List {
        /// Set the display type
        ///
        /// The display type can be one of the following:
        /// tabular: display content in a table format
        /// json: return data in json format
        /// yaml: return data in yaml format
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
    /// Add new servers to IML
    #[structopt(name = "add")]
    Add(AddHosts),
    /// Remove servers from IML
    #[structopt(name = "remove")]
    Remove(RemoveHosts),
    /// Remove servers from IML DB, but leave agents in place.
    /// Takes a hostlist expression of servers to remove.
    #[structopt(name = "force-remove")]
    ForceRemove { hosts: String },
    /// Work with Server Profiles
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
    Confirm::new()
        .with_prompt("Continue deployment?")
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

fn list_server(hosts: Vec<Host>, display_type: DisplayType) {
    let term = Term::stdout();

    tracing::debug!("Hosts: {:?}", hosts);

    let x = hosts.into_display_type(display_type);

    term.write_line(&x).unwrap();
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
        display_cancelled(format!("Host {} already known to IML. Please remove first if attempting to complete deployment.", known_host.fqdn));
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
) -> Result<Objects<CmdWrapper>, ImlManagerCliError> {
    Ok(post("test_host", Objects { objects })
        .await?
        .error_for_status()?
        .json::<Objects<CmdWrapper>>()
        .await
        .map_err(iml_manager_client::ImlManagerClientError::Reqwest)?)
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
        .filter_map(|job| iml_api_utils::extract_id(&job).map(|x| x.to_string()))
        .map(|x| ["id__in".into(), x])
        .chain(iter::once(["limit".into(), "0".into()]))
        .collect()
}

fn all_jobs_passed(jobs: ApiList<TestHostJob>, term: &Term) -> bool {
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
            } else {
                state
            }
        })
}

fn handle_test_host_failure(all_passed: bool, config: &AddHosts) -> Result<(), ImlManagerCliError> {
    if !all_passed {
        let error_msg = "Preflight checks failed";

        display_error(&error_msg);

        if !can_continue(config) {
            return Err(ImlManagerCliError::ApiError(error_msg.into()));
        }
    }

    Ok(())
}

fn get_agent_config_objects<'a>(
    new_hosts: &'a BTreeSet<String>,
    agent_profile: &'a ServerProfile,
    auth: &AuthType,
) -> Vec<AgentConfig<'a>> {
    new_hosts
        .iter()
        .map(|address| AgentConfig {
            info: TestHostConfig::new(&address, &auth),
            server_profile: &agent_profile.resource_uri,
        })
        .collect()
}

async fn post_command_to_host<'a>(
    objects: Vec<AgentConfig<'a>>,
) -> Result<Objects<CommandAndHostWrapper>, ImlManagerCliError> {
    Ok(post(Host::endpoint_name(), Objects { objects })
        .await?
        .json()
        .await
        .map_err(iml_manager_client::ImlManagerClientError::Reqwest)?)
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

fn get_host_ids(hosts: &[Host]) -> Vec<[String; 2]> {
    hosts
        .iter()
        .map(|x| ["id__in".into(), x.id.to_string()])
        .chain(iter::once(["limit".into(), "0".into()]))
        .collect()
}

fn filter_host_profiles<I>(profile: &ServerProfile, objects: I) -> Vec<(u32, Vec<ProfileTest>)>
where
    I: IntoIterator<Item = HostProfileWrapper>,
{
    objects
        .into_iter()
        .filter_map(|x| x.host_profiles)
        .filter_map(|mut x| x.profiles.remove(&profile.name).map(|p| (x.host, p)))
        .collect()
}

fn filter_profile_tests(objects: &[(u32, Vec<ProfileTest>)]) -> Vec<(&u32, Vec<&ProfileTest>)> {
    objects
        .iter()
        .map(|(k, tests)| (k, tests.iter().filter(|y| !y.pass).collect::<Vec<_>>()))
        .filter(|(_, tests)| !tests.is_empty())
        .collect()
}

fn handle_invalid_profile_tests(
    term: &Term,
    config: &AddHosts,
    profile: &ServerProfile,
    hosts: &[Host],
    invalid: Vec<(&u32, Vec<&ProfileTest>)>,
) -> Result<(), ImlManagerCliError> {
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

    Ok(())
}

fn get_host_profile_configs<'a>(
    profile: &'a ServerProfile,
    objects: &[(u32, Vec<ProfileTest>)],
) -> Vec<HostProfileConfig<'a>> {
    objects
        .iter()
        .map(|(host, _)| HostProfileConfig {
            host: *host,
            profile: &profile.name,
        })
        .collect()
}

async fn post_profile<'a>(
    objects: Vec<HostProfileConfig<'a>>,
) -> Result<Objects<HostProfileCmdWrapper>, ImlManagerCliError> {
    Ok(post(HostProfile::endpoint_name(), Objects { objects })
        .await?
        .json()
        .await
        .map_err(iml_manager_client::ImlManagerClientError::Reqwest)?)
}

fn get_commands_from_wrapper(objects: Vec<HostProfileCmdWrapper>) -> Vec<Command> {
    objects
        .into_iter()
        .flat_map(|HostProfileCmdWrapper { commands }| commands)
        .collect()
}

async fn process_addhosts(
    config: &AddHosts,
    api_hosts: &[Host],
    new_hosts: BTreeSet<String>,
) -> Result<(BTreeSet<String>, AuthType), ImlManagerCliError> {
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
) -> Result<bool, ImlManagerCliError> {
    let objects = get_test_host_configs(&new_hosts, auth);

    let Objects { objects } = post_test_host(objects).await?;

    let cmds = get_commands_from_objects(objects);

    tracing::debug!("cmds {:?}", cmds);

    term.write_line(&format!("{} preflight checks...", style("Running").green()))?;

    let cmds = wait_for_cmds(&cmds).await?;

    let jobs = get_jobs_from_commands(cmds);

    let jobs: ApiList<TestHostJob> = get(TestHostJob::endpoint_name(), jobs).await?;

    tracing::debug!("jobs {:?}", jobs);

    let all_passed = all_jobs_passed(jobs, term);

    Ok(all_passed)
}

async fn deploy_agents(
    term: &Term,
    new_hosts: &BTreeSet<String>,
    agent_profile: &ServerProfile,
    server_profile: &ServerProfile,
    auth: &AuthType,
) -> Result<Vec<Host>, ImlManagerCliError> {
    let objects = get_agent_config_objects(new_hosts, agent_profile, auth);

    let Objects { objects }: Objects<CommandAndHostWrapper> = post_command_to_host(objects).await?;

    tracing::debug!("command and hosts {:?}", objects);

    let (commands, hosts): (Vec<_>, Vec<_>) = get_commands_and_hosts_from_objects(objects);

    term.write_line(&format!("{} agents...", style("Deploying").green()))?;

    wait_for_cmds_success(&commands).await?;

    wrap_fut(
        "Waiting for agents to restart...",
        wait_till_agent_starts(&hosts, &server_profile.name),
    )
    .await?;

    Ok(hosts)
}

async fn handle_profiles(
    term: &Term,
    config: &AddHosts,
    hosts: &[Host],
    profile: &ServerProfile,
) -> Result<Vec<Command>, ImlManagerCliError> {
    let host_ids = get_host_ids(hosts);

    let ApiList { objects, .. }: ApiList<HostProfileWrapper> =
        get(HostProfile::endpoint_name(), host_ids).await?;

    tracing::debug!("Host Profiles {:?}", objects);

    let objects = filter_host_profiles(profile, objects);

    let invalid = filter_profile_tests(&objects);

    handle_invalid_profile_tests(term, config, profile, hosts, invalid)?;

    let objects = get_host_profile_configs(&profile, &objects);

    let Objects { objects } = post_profile(objects).await?;

    tracing::debug!("Host Profile resp {:?}", objects);

    let cmds: Vec<Command> = get_commands_from_wrapper(objects);

    term.write_line(&format!("{} host profiles...", style("Setting").green()))?;

    Ok(cmds)
}

async fn add_server(config: AddHosts) -> Result<(), ImlManagerCliError> {
    let term = Term::stdout();

    let new_hosts = hostlist_parser::parse(&config.hosts)?;

    tracing::debug!("Parsed hosts {:?}", new_hosts);

    let (profiles, api_hosts): (ApiList<ServerProfile>, ApiList<Host>) =
        future::try_join(get_all(), get_all()).await?;

    let server_profile = get_profile_by_name(&profiles.objects, &config.profile)
        .ok_or_else(|| not_found_err(format!("{} profile not found.", &config.profile)))?;

    let agent_profile = get_agent_profile(server_profile, &profiles.objects)?;

    let (new_hosts, auth) = process_addhosts(&config, &api_hosts.objects, new_hosts).await?;

    if new_hosts.is_empty() {
        return Err(not_found_err("No new hosts found"));
    }

    tracing::debug!("AUTH: {:?}", auth);

    let all_passed = get_test_host_commands_and_jobs(&term, &new_hosts, &auth).await?;

    handle_test_host_failure(all_passed, &config)?;

    let hosts = deploy_agents(&term, &new_hosts, &agent_profile, &server_profile, &auth).await?;

    let cmds = handle_profiles(&term, &config, &hosts, &server_profile).await?;

    wait_for_cmds_success(&cmds).await?;

    Ok(())
}

/// Given a server_profile to deploy,
/// figures out the profile that should be used to deploy the agents
fn get_agent_profile<'a>(
    profile: &ServerProfile,
    xs: &'a [ServerProfile],
) -> Result<&'a ServerProfile, Error> {
    let name = if profile.repolist.is_empty() {
        "default_baseless"
    } else {
        "default"
    };

    let x = xs
        .iter()
        .find(|x| x.name == name)
        .ok_or_else(|| Error::new(ErrorKind::NotFound, format!("{} profile not found.", name)))?;

    Ok(x)
}

pub async fn server_cli(command: ServerCommand) -> Result<(), ImlManagerCliError> {
    match command {
        ServerCommand::List { display_type } => {
            let hosts: ApiList<Host> = wrap_fut("Fetching hosts...", get_hosts()).await?;
            list_server(hosts.objects, display_type);
        }
        ServerCommand::Add(config) => add_server(config).await?,
        ServerCommand::ForceRemove { hosts } => {
            let remove_hosts = hostlist_parser::parse(&hosts)?;

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

                    Ok::<_, ImlManagerCliError>(command)
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

fn not_found_err(x: impl Into<String>) -> ImlManagerCliError {
    Error::new(ErrorKind::NotFound, x.into()).into()
}
