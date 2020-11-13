// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{
        create_command, get_all, get_hosts, get_influx, get_one, graphql, wait_for_cmds_success,
        SendCmd, SendJob,
    },
    display_utils::{usage, wrap_fut, DisplayType, IntoDisplayType as _},
    error::ImlManagerCliError,
    ostpool::{ostpool_cli, OstPoolCommand},
};
use console::Term;
use futures::future::{try_join, try_join5};
use iml_graphql_queries::{client_mount, target as target_queries};
use iml_wire_types::{db::TargetKind, Filesystem};
use number_formatter::{format_bytes, format_number};
use prettytable::{Row, Table};
use std::collections::{BTreeMap, HashMap};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum FilesystemCommand {
    /// List all configured filesystems
    #[structopt(name = "list")]
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
    /// Show filesystem
    #[structopt(name = "show")]
    Show {
        #[structopt(name = "FSNAME")]
        fsname: String,
    },
    /// Ost Pools
    #[structopt(name = "pool")]
    Pool {
        #[structopt(subcommand)]
        command: OstPoolCommand,
    },
    /// Detect existing filesystem
    #[structopt(name = "detect")]
    Detect {
        #[structopt(short, long)]
        hosts: Option<String>,
    },
    /// Client mount command
    #[structopt(name = "list-client-mount")]
    ClientMount {
        #[structopt(name = "fsname")]
        fsname: String,
    },
}

fn option_sub(a: Option<u64>, b: Option<u64>) -> Option<u64> {
    Some(a?.saturating_sub(b?))
}

async fn detect_filesystem(hosts: Option<String>) -> Result<(), ImlManagerCliError> {
    let hosts = if let Some(hl) = hosts {
        let hostlist = hostlist_parser::parse(&hl)?;
        tracing::debug!("Host Names: {:?}", hostlist);
        let all_hosts = get_hosts().await?;

        let hostmap: BTreeMap<&str, &str> = all_hosts
            .objects
            .iter()
            .map(|h| {
                vec![
                    (h.nodename.as_str(), h.resource_uri.as_str()),
                    (h.fqdn.as_str(), h.resource_uri.as_str()),
                ]
            })
            .flatten()
            .collect();

        hostlist
            .iter()
            .filter_map(|h| hostmap.get(h.as_str()))
            .map(|x| (*x).to_string())
            .collect()
    } else {
        vec![]
    };

    tracing::debug!("Host APIs: {:?}", hosts);

    let args = if hosts.is_empty() {
        vec![]
    } else {
        vec![("hosts".to_string(), hosts)]
    };

    let cmd = SendCmd {
        message: "Detecting filesystems".into(),
        jobs: vec![SendJob::<HashMap<String, Vec<String>>> {
            class_name: "DetectTargetsJob".into(),
            args: args.into_iter().collect(),
        }],
    };
    let cmd = wrap_fut("Detecting filesystems...", create_command(cmd)).await?;

    wait_for_cmds_success(&[cmd]).await?;
    Ok(())
}

pub async fn filesystem_cli(command: FilesystemCommand) -> Result<(), ImlManagerCliError> {
    match command {
        FilesystemCommand::List { display_type } => {
            let fut_fs = get_all::<Filesystem>();
            let query = iml_influx::filesystems::query();
            let fut_st =
                get_influx::<iml_influx::filesystems::InfluxResponse>("iml_stats", query.as_str());

            let (mut filesystems, influx_resp) =
                wrap_fut("Fetching filesystems...", try_join(fut_fs, fut_st)).await?;
            let stats = iml_influx::filesystems::Response::from(influx_resp);

            tracing::debug!("FSs: {:?}", filesystems);
            tracing::debug!("Stats: {:?}", stats);

            filesystems.objects.iter_mut().for_each(|x| {
                let s = stats.get(&x.name).cloned().unwrap_or_default();

                x.bytes_free = s.bytes_free.map(|x| x as f64);
                x.bytes_total = s.bytes_total.map(|x| x as f64);
                x.files_free = s.files_free;
                x.files_total = s.files_total;
                x.client_count = s.clients;
            });

            let term = Term::stdout();

            tracing::debug!("Filesystems: {:?}", filesystems);

            let x = filesystems.objects.into_display_type(display_type);

            term.write_line(&x).unwrap();
        }
        FilesystemCommand::Show { fsname } => {
            let fut_fs = get_one::<Filesystem>(vec![("name", &fsname)]);

            let query = iml_influx::filesystem::query(&fsname);
            let fut_st =
                get_influx::<iml_influx::filesystem::InfluxResponse>("iml_stats", query.as_str());

            let targets = graphql(target_queries::list::build(
                None,
                None,
                None,
                Some(&fsname),
                None,
            ));

            let (fs, influx_resp, hosts, targets_resp, client_mount_cmd): (
                _,
                _,
                _,
                iml_graphql_queries::Response<target_queries::list::Resp>,
                _,
            ) = wrap_fut(
                "Fetching filesystem...",
                try_join5(
                    fut_fs,
                    fut_st,
                    get_hosts(),
                    targets,
                    get_fs_mount_cmd(&fsname),
                ),
            )
            .await?;
            let st = iml_influx::filesystem::Response::from(influx_resp);

            tracing::debug!("FS: {:?}", fs);
            tracing::debug!("ST: {:?}", st);
            tracing::debug!("Targets: {:?}", targets_resp);

            let targets = Result::from(targets_resp)?.data.targets;

            let (mgs, mdts, osts) =
                targets
                    .into_iter()
                    .fold(("---", vec![], vec![]), |mut acc, x| {
                        match x.get_kind() {
                            TargetKind::Mgt => {
                                x.active_host_id
                                    .and_then(|x| hosts.objects.iter().find(|y| y.id == x))
                                    .map(|x| x.fqdn.as_str())
                                    .map(|x| {
                                        acc.0 = x;
                                    });
                            }
                            TargetKind::Mdt => acc.1.push(x.name),
                            TargetKind::Ost => acc.2.push(x.name),
                        }

                        acc
                    });

            Table::init(vec![
                Row::from(&["Name".to_string(), fs.label]),
                Row::from(&[
                    "Space Used/Avail".to_string(),
                    usage(
                        option_sub(st.bytes_total, st.bytes_free),
                        st.bytes_avail,
                        format_bytes,
                    ),
                ]),
                Row::from(&[
                    "Inodes Used/Avail".to_string(),
                    usage(
                        option_sub(st.files_total, st.files_free),
                        st.files_total,
                        format_number,
                    ),
                ]),
                Row::from(&["State".to_string(), fs.state]),
                Row::from(&["Management Server", mgs]),
                Row::from(&["MDTs".to_string(), mdts.join("\n")]),
                Row::from(&["OSTs".to_string(), osts.join("\n")]),
                Row::from(&[
                    "Clients".to_string(),
                    format!("{}", st.clients.unwrap_or(0)),
                ]),
                Row::from(&["Mount Path".to_string(), client_mount_cmd]),
            ])
            .printstd();
        }
        FilesystemCommand::ClientMount { fsname } => {
            let cmd = get_fs_mount_cmd(&fsname).await?;

            let term = Term::stdout();
            term.write_line(&cmd).unwrap();
        }
        FilesystemCommand::Pool { command } => ostpool_cli(command).await?,
        FilesystemCommand::Detect { hosts } => detect_filesystem(hosts).await?,
    };

    Ok(())
}

async fn get_fs_mount_cmd(fsname: &str) -> Result<String, ImlManagerCliError> {
    let query = client_mount::list::build(fsname);

    let resp: iml_graphql_queries::Response<client_mount::list::Resp> =
        wrap_fut("Fetching client mount", graphql(query)).await?;

    let x = Result::from(resp)?.data.client_mount_command;

    Ok(x)
}
