// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{get, get_all, get_one, post},
    display_utils::{generate_table, wrap_fut},
    error::ImlManagerCliError,
};
use futures::future::try_join_all;
use iml_wire_types::{ApiList, EndpointName, Filesystem, FlatQuery, OstPool};
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
            let xs = match fsname {
                Some(fsname) => {
                    let fs: Filesystem =
                        wrap_fut("Fetching Filesystem ...", get_one(vec![("name", &fsname)])).await?;
                    let pools: ApiList<OstPool> = wrap_fut(
                        "Fetching OstPools...",
                        get(
                            OstPool::endpoint_name(),
                            vec![("limit", 0), ("filesystem", fs.id)],
                        ),
                    )
                    .await?;
                    pools
                        .objects
                        .into_iter()
                        .map(|p| vec![fsname.clone(), p.name, p.osts.len().to_string()])
                        .collect()
                }
                None => {
                    let pools: ApiList<OstPool> =
                        wrap_fut("Fetching OstPools...", get_all()).await?;
                    // @@ "cache" this
                    try_join_all(pools.objects.into_iter().map(|p| {
                        async move {
                            get(&p.filesystem, Filesystem::query()).await.map(
                                move |fs: Filesystem| {
                                    vec![fs.name, p.name, p.osts.len().to_string()]
                                },
                            )
                        }
                    }))
                    .await?
                }
            };

            let table = generate_table(&["Filesystem", "Pool Name", "OST Count"], xs);
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
            wrap_fut("Creating OstPool...", post(OstPool::endpoint_name(), pool)).await?;
        }
        _ => println!("NYI"),
    };
    Ok(())
}
