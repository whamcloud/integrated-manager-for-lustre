// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{get, get_all, post},
    display_utils::{generate_table, wrap_fut},
    error::ImlManagerCliError,
};
use iml_wire_types::{ApiList, EndpointName, OstPool};
use structopt::StructOpt;

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct Objects<T> {
    objects: Vec<T>,
}

#[derive(Debug, StructOpt)]
pub enum OstPoolCommand {
    /// List all pools for filesystem
    #[structopt(name = "list")]
    List {
        #[structopt(name = "FSNAME")]
        fsname: Option<String>,
    },

    /// Show Pool Details
    #[structopt(name = "show")]
    Show {
        #[structopt(name = "FSNAME")]
        fsname: String,
        poolname: String,
    },

    /// Create Pool
    #[structopt(name = "create")]
    Create {
        fsname: String,
        poolname: String,
        osts: Vec<String>,
    },

    /// Add OST to Pool
    #[structopt(name = "grow")]
    Grow {
        fsname: String,
        poolname: String,
        ost: String,
    },

    /// Remove OST to Pool
    #[structopt(name = "shrink")]
    Shrink {
        fsname: String,
        poolname: String,
        ost: String,
    },

    /// Destroy Pool
    #[structopt(name = "destroy")]
    Destroy { fsname: String, poolname: String },
}

pub async fn ostpool_cli(command: OstPoolCommand) -> Result<(), ImlManagerCliError> {
    match command {
        OstPoolCommand::List { fsname } => {
            let pools: ApiList<OstPool> = match fsname {
                Some(fsname) => {
                    wrap_fut(
                        "Fetching OstPools...",
                        get(OstPool::endpoint_name(), vec!["filesystem", &fsname]),
                    )
                    .await?
                }
                None => wrap_fut("Fetching OstPools...", get_all()).await?,
            };
            let table = generate_table(
                &["Filesystem", "Pool Name", "OST Count"],
                pools
                    .objects
                    .into_iter()
                    .map(|p| vec![p.filesystem, p.name, p.osts.len().to_string()]),
            );
            table.printstd();
        }
        OstPoolCommand::Create {
            fsname,
            poolname,
            osts,
        } => {
            let pool = OstPool {
                filesystem: fsname,
                name: poolname,
                osts,
            };
            wrap_fut(
                "Creating OstPool...",
                post(
                    OstPool::endpoint_name(),
                    Objects {
                        objects: vec![pool],
                    },
                ),
            )
            .await?;
        }
        _ => println!("NYI"),
    };
    Ok(())
}
