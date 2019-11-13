// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{get, get_all, get_one},
    display_utils::{generate_table, wrap_fut},
    error::ImlManagerCliError,
    ostpool::{ostpool_cli, OstPoolCommand},
};
use futures::future::{try_join, try_join_all};
use iml_wire_types::{ApiList, Filesystem, FlatQuery, Mgt, Ost};
use number_formatter::{format_bytes, format_number};
use prettytable::{Row, Table};
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
}

fn usage(
    free: Option<f64>,
    total: Option<f64>,
    formatter: fn(f64, Option<usize>) -> String,
) -> String {
    match (free, total) {
        (Some(free), Some(total)) => format!(
            "{} / {}",
            formatter(total - free, Some(0)),
            formatter(total, Some(0))
        ),
        (None, Some(total)) => format!("Calculating ... / {}", formatter(total, Some(0))),
        _ => "Calculating ...".to_string(),
    }
}

pub async fn filesystem_cli(command: FilesystemCommand) -> Result<(), ImlManagerCliError> {
    match command {
        FilesystemCommand::List => {
            let filesystems: ApiList<Filesystem> =
                wrap_fut("Fetching filesystems...", get_all()).await?;

            tracing::debug!("FSs: {:?}", filesystems);

            let table = generate_table(
                &[
                    "Name", "State", "Space", "Inodes", "Clients", "MDTs", "OSTs",
                ],
                filesystems.objects.into_iter().map(|f| {
                    vec![
                        f.label,
                        f.state,
                        usage(f.bytes_free, f.bytes_total, format_bytes),
                        usage(f.files_free, f.files_total, format_number),
                        format_number(f.client_count.unwrap_or(0.0), Some(0)),
                        f.mdts.len().to_string(),
                        f.osts.len().to_string(),
                    ]
                }),
            );

            table.printstd();
        }
        FilesystemCommand::Show { fsname } => {
            let fs: Filesystem = wrap_fut("Fetching filesystem...", get_one(vec![("name", &fsname)])).await?;

            tracing::debug!("FS: {:?}", fs);

            let (mgt, osts): (Mgt, Vec<Ost>) = try_join(
                wrap_fut("Fetching MGT...", get(&fs.mgt, Mgt::query())),
                try_join_all(fs.osts.into_iter().map(|o| {
                    async move { wrap_fut("Fetching OST...", get(&o, Ost::query())).await }
                })),
            )
            .await?;

            let mut table = Table::new();
            table.add_row(Row::from(&["Name".to_string(), fs.label]));
            table.add_row(Row::from(&[
                "Space".to_string(),
                usage(fs.bytes_free, fs.bytes_total, format_bytes),
            ]));
            table.add_row(Row::from(&[
                "Inodes".to_string(),
                usage(fs.files_free, fs.files_total, format_number),
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
                format!("{:0}", fs.client_count.unwrap_or(0.0)),
            ]));
            table.add_row(Row::from(&["Mount Path".to_string(), fs.mount_path]));
            table.printstd();
        }
        FilesystemCommand::Pool { command } => ostpool_cli(command).await?,
    };

    Ok(())
}
