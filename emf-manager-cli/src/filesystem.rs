// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{get_all, get_hosts, get_influx, get_one, graphql, put, wait_for_cmds_success},
    display_utils::{usage, wrap_fut, DisplayType, IntoDisplayType as _},
    error::EmfManagerCliError,
    ostpool::{ostpool_cli, OstPoolCommand},
};
use console::Term;
use emf_graphql_queries::{client_mount, filesystem as fs_queries, target as target_queries};
use emf_wire_types::{db::TargetKind, CmdWrapper, Filesystem};
use futures::future::{try_join, try_join5};
use number_formatter::{format_bytes, format_number};
use prettytable::{Row, Table};
use structopt::StructOpt;

#[derive(serde::Serialize, serde::Deserialize)]
struct StateChange {
    state: String,
}

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
    Detect,
    /// Forget existing filesystem
    /// This will remove knowledge of the filesystem
    /// from the manager, but will not effect it on storage servers
    #[structopt(name = "forget")]
    Forget {
        #[structopt(name = "FSNAME")]
        fs_name: String,
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

async fn detect_filesystem() -> Result<(), EmfManagerCliError> {
    let query = fs_queries::detect::build();

    let resp: emf_graphql_queries::Response<fs_queries::detect::Resp> =
        wrap_fut("Detecting Filesystem...", graphql(query)).await?;

    let _ = Result::from(resp)?;

    let term = Term::stdout();

    term.write_line("Detected Filesystems").unwrap();

    Ok(())
}

async fn forget_filesystem(fsname: String) -> Result<(), EmfManagerCliError> {
    let fs = wrap_fut(
        "Fetching Filesystem...",
        get_one::<Filesystem>(vec![("name", &fsname)]),
    )
    .await?;

    let r = put(
        &fs.resource_uri,
        StateChange {
            state: "forgotten".into(),
        },
    )
    .await?
    .error_for_status()?;

    let CmdWrapper { command } = r.json().await?;

    wait_for_cmds_success(&[command]).await?;

    Ok(())
}

pub async fn filesystem_cli(command: FilesystemCommand) -> Result<(), EmfManagerCliError> {
    match command {
        FilesystemCommand::List { display_type } => {
            let fut_fs = get_all::<Filesystem>();
            let query = emf_influx::filesystems::query();
            let fut_st =
                get_influx::<emf_influx::filesystems::InfluxResponse>("emf_stats", query.as_str());

            let (mut filesystems, influx_resp) =
                wrap_fut("Fetching filesystems...", try_join(fut_fs, fut_st)).await?;
            let stats = emf_influx::filesystems::Response::from(influx_resp);

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

            let query = emf_influx::filesystem::query(&fsname);
            let fut_st =
                get_influx::<emf_influx::filesystem::InfluxResponse>("emf_stats", query.as_str());

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
                emf_graphql_queries::Response<target_queries::list::Resp>,
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
            let st = emf_influx::filesystem::Response::from(influx_resp);

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
                                if let Some(x) = x
                                    .active_host_id
                                    .and_then(|x| hosts.objects.iter().find(|y| y.id == x))
                                    .map(|x| x.fqdn.as_str())
                                {
                                    acc.0 = x;
                                }
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
        FilesystemCommand::Detect => detect_filesystem().await?,
        FilesystemCommand::Forget { fs_name } => forget_filesystem(fs_name).await?,
    };

    Ok(())
}

async fn get_fs_mount_cmd(fsname: &str) -> Result<String, EmfManagerCliError> {
    let query = client_mount::list_mount_command::build(fsname);

    let resp: emf_graphql_queries::Response<client_mount::list_mount_command::Resp> =
        wrap_fut("Fetching client mount", graphql(query)).await?;

    let x = Result::from(resp)?.data.client_mount_command;

    Ok(x)
}
