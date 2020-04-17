// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{
        create_command, get, get_all, get_hosts, get_influx, get_one, wait_for_cmds_success,
        SendCmd, SendJob,
    },
    display_utils::{generate_table, wrap_fut},
    error::ImlManagerCliError,
    ostpool::{ostpool_cli, OstPoolCommand},
};
use futures::future::{try_join, try_join_all};
use iml_wire_types::{Filesystem, FlatQuery, Mgt, Ost};
use number_formatter::{format_bytes, format_number};
use prettytable::{Row, Table};
use std::collections::{BTreeMap, HashMap};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum FilesystemCommand {
    /// List all configured filesystems
    #[structopt(name = "list")]
    List,
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
}

fn option_sub(a: Option<u64>, b: Option<u64>) -> Option<u64> {
    Some(a?.saturating_sub(b?))
}

fn usage(
    used: Option<u64>,
    total: Option<u64>,
    formatter: fn(f64, Option<usize>) -> String,
) -> String {
    format!(
        "{} / {}",
        used.map(|u| formatter(u as f64, Some(0)))
            .as_deref()
            .unwrap_or("---"),
        total
            .map(|t| formatter(t as f64, Some(0)))
            .as_deref()
            .unwrap_or("---")
    )
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
        FilesystemCommand::List => {
            let fut_fs = get_all::<Filesystem>();
            let query = iml_influx::filesystems::query();
            let fut_st =
                get_influx::<iml_influx::filesystems::InfluxResponse>("iml_stats", query.as_str());

            let (filesystems, influx_resp) =
                wrap_fut("Fetching filesystems...", try_join(fut_fs, fut_st)).await?;
            let stats = iml_influx::filesystems::Response::from(influx_resp);

            tracing::debug!("FSs: {:?}", filesystems);
            tracing::debug!("Stats: {:?}", stats);

            let table = generate_table(
                &[
                    "Name",
                    "State",
                    "Space Used/Total",
                    "Inodes Used/Total",
                    "Clients",
                    "MDTs",
                    "OSTs",
                ],
                filesystems.objects.into_iter().map(|f| {
                    let s = stats.get(&f.name).cloned().unwrap_or_default();
                    vec![
                        f.label,
                        f.state,
                        usage(
                            option_sub(s.bytes_total, s.bytes_free),
                            s.bytes_avail,
                            format_bytes,
                        ),
                        usage(
                            option_sub(s.files_total, s.files_free),
                            s.files_total,
                            format_number,
                        ),
                        format!("{}", s.clients.unwrap_or(0)),
                        f.mdts.len().to_string(),
                        f.osts.len().to_string(),
                    ]
                }),
            );

            table.printstd();
        }
        FilesystemCommand::Show { fsname } => {
            let fut_fs = get_one::<Filesystem>(vec![("name", &fsname)]);
            let query = iml_influx::filesystem::query(&fsname);
            let fut_st =
                get_influx::<iml_influx::filesystem::InfluxResponse>("iml_stats", query.as_str());

            let (fs, influx_resp) =
                wrap_fut("Fetching filesystem...", try_join(fut_fs, fut_st)).await?;
            let st = iml_influx::filesystem::Response::from(influx_resp);

            tracing::debug!("FS: {:?}", fs);
            tracing::debug!("ST: {:?}", st);

            let (mgt, osts): (Mgt, Vec<Ost>) = try_join(
                wrap_fut("Fetching MGT...", get(&fs.mgt, Mgt::query())),
                try_join_all(fs.osts.into_iter().map(|o| async move {
                    wrap_fut("Fetching OST...", get(&o, Ost::query())).await
                })),
            )
            .await?;

            let mut table = Table::new();
            table.add_row(Row::from(&["Name".to_string(), fs.label]));
            table.add_row(Row::from(&[
                "Space Used/Total".to_string(),
                usage(
                    option_sub(st.bytes_total, st.bytes_free),
                    st.bytes_avail,
                    format_bytes,
                ),
            ]));
            table.add_row(Row::from(&[
                "Inodes Used/Total".to_string(),
                usage(
                    option_sub(st.files_total, st.files_free),
                    st.files_total,
                    format_number,
                ),
            ]));
            table.add_row(Row::from(&["State".to_string(), fs.state]));
            table.add_row(Row::from(&[
                "Management Server".to_string(),
                mgt.active_host_name,
            ]));

            let mdtnames: Vec<String> = fs.mdts.into_iter().map(|m| m.name).collect();
            table.add_row(Row::from(&["MDTs".to_string(), mdtnames.join("\n")]));

            let ostnames: Vec<String> = osts.into_iter().map(|m| m.name).collect();
            table.add_row(Row::from(&["OSTs".to_string(), ostnames.join("\n")]));

            table.add_row(Row::from(&[
                "Clients".to_string(),
                format!("{}", st.clients.unwrap_or(0)),
            ]));
            table.add_row(Row::from(&["Mount Path".to_string(), fs.mount_path]));
            table.printstd();
        }
        FilesystemCommand::Pool { command } => ostpool_cli(command).await?,
        FilesystemCommand::Detect { hosts } => detect_filesystem(hosts).await?,
    };

    Ok(())
}
