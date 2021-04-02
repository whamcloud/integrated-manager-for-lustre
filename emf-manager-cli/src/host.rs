// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{get_hosts, graphql},
    display_utils::{print_command_show_message, wrap_fut, DisplayType, IntoDisplayType as _},
    error::EmfManagerCliError,
};
use console::Term;
use emf_graphql_queries::host as host_queries;
use emf_wire_types::{ssh::SshOpts, CommandOrDryRun, Flavor};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
struct Config {
    /// A hostlist expression of FQDNs to deploy the service-mesh onto. Supports multiple hostlists
    #[structopt(required = true)]
    fqdns: Vec<String>,
    /// The type of server to deploy
    #[structopt(required = true, long, possible_values = &["server", "client", "ubuntu", "ubuntu_dgx"], case_insensitive = true)]
    flavor: Flavor,
    /// Return the generated input document instead of running it on the state machine.
    /// The document can later be executed with the `emf run` command.
    #[structopt(long)]
    dry_run: bool,
}

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub struct Deploy {
    #[structopt(flatten)]
    config: Config,
    #[structopt(flatten)]
    ssh_opts: SshOpts,
}

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum Command {
    /// List all configured hosts (default)
    #[structopt(name = "list")]
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
    /// Deploy EMF services to the given FQDNs and wait for them to report back in
    Deploy(Deploy),
}

async fn list(display_type: DisplayType) -> Result<(), EmfManagerCliError> {
    let hosts = get_hosts().await?;

    let term = Term::stdout();

    tracing::debug!(?hosts);

    let x = hosts.into_display_type(display_type);

    term.write_line(&x).unwrap();

    Ok(())
}

pub async fn cli(command: Option<Command>) -> Result<(), EmfManagerCliError> {
    host(command.unwrap_or(Command::List {
        display_type: DisplayType::Tabular,
    }))
    .await
}

async fn host(command: Command) -> Result<(), EmfManagerCliError> {
    match command {
        Command::List { display_type } => list(display_type).await?,
        Command::Deploy(Deploy { config, ssh_opts }) => {
            let query = host_queries::deploy::build(
                config.fqdns,
                config.flavor,
                config.dry_run,
                ssh_opts.port,
                ssh_opts.user,
                ssh_opts.auth_opts,
                ssh_opts.proxy_opts,
            );

            let resp: emf_graphql_queries::Response<host_queries::deploy::Resp> =
                wrap_fut("Deploying Hosts...", graphql(query)).await?;

            let x = Result::from(resp)?.data.host.deploy;

            tracing::debug!(?x);

            match x {
                CommandOrDryRun::Command(x) => {
                    println!("Plan submitted.");

                    print_command_show_message(&x);
                }
                CommandOrDryRun::DryRun(x) => {
                    println!("{}", x.yaml);
                }
            }
        }
    };

    Ok(())
}
