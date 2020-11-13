// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{delete, get, get_all, get_one, post, put, wait_for_cmds_success},
    display_utils::{wrap_fut, DisplayType, IntoDisplayType as _},
    error::ImlManagerCliError,
};
use console::{style, Term};
use futures::future::try_join_all;
use iml_wire_types::{ApiList, Command, EndpointName, Filesystem, FlatQuery, OstPool, OstPoolApi};
use prettytable::{Row, Table};
use std::iter::FromIterator;
use structopt::StructOpt;

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct ObjCommand {
    command: Command,
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct ObjCommands {
    commands: Vec<Command>,
}

#[derive(Debug, StructOpt)]
pub enum OstPoolCommand {
    /// List all pools for filesystem
    #[structopt(name = "list")]
    List {
        #[structopt(name = "FSNAME")]
        fsname: Option<String>,

        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
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
        osts: Vec<String>,
    },

    /// Remove OST to Pool
    #[structopt(name = "shrink")]
    Shrink {
        fsname: String,
        poolname: String,
        osts: Vec<String>,
    },

    /// Destroy Pool
    #[structopt(name = "destroy")]
    Destroy { fsname: String, poolname: String },
}

#[derive(Debug, serde::Deserialize)]
struct Target {
    name: String,
}

async fn pool_lookup(fsname: &str, poolname: &str) -> Result<OstPoolApi, ImlManagerCliError> {
    let fs: Filesystem =
        wrap_fut("Fetching Filesystem ...", get_one(vec![("name", fsname)])).await?;

    let mut pool: OstPoolApi = wrap_fut(
        "Fetching OstPool...",
        get_one(vec![
            ("filesystem", fs.id.to_string().as_str()),
            ("name", poolname),
        ]),
    )
    .await?;

    let osts: Vec<String> = try_join_all(pool.ost.osts.into_iter().map(|o| async move {
        wrap_fut(
            "Fetching OST...",
            get(&o, vec![("limit", "0"), ("dehydrate__volume", "false")]),
        )
        .await
        .map(|m: Target| m.name)
    }))
    .await?;
    pool.ost.osts = osts;
    Ok(pool)
}

async fn ostpool_list(
    fsname: Option<String>,
    display_type: DisplayType,
) -> Result<(), ImlManagerCliError> {
    let xs: Vec<OstPool> = match fsname {
        Some(fsname) => {
            let fs: Filesystem =
                wrap_fut("Fetching Filesystem ...", get_one(vec![("name", &fsname)])).await?;

            let pools: ApiList<OstPoolApi> = wrap_fut(
                "Fetching OstPools...",
                get(
                    OstPoolApi::endpoint_name(),
                    vec![("limit", 0), ("filesystem", fs.id)],
                ),
            )
            .await?;

            pools
                .objects
                .into_iter()
                .map(|mut x| {
                    x.ost.filesystem = fs.name.clone();
                    x.ost
                })
                .collect()
        }
        None => {
            let pools: ApiList<OstPoolApi> = wrap_fut("Fetching OstPools...", get_all()).await?;

            let fs_ids = pools
                .objects
                .iter()
                .filter_map(|p| {
                    let id = iml_api_utils::extract_id(&p.ost.filesystem);

                    id.map(|x| x.to_string())
                })
                .collect::<std::collections::HashSet<String>>();

            let fs_ids = Vec::from_iter(fs_ids).join(",");

            let mut query = Filesystem::query();

            query.push(("id__in", &fs_ids));

            let fs: ApiList<Filesystem> = get(Filesystem::endpoint_name(), query).await?;

            pools
                .objects
                .into_iter()
                .filter_map(move |mut p| {
                    fs.objects
                        .iter()
                        .find(|f| f.resource_uri == p.ost.filesystem)
                        .map(move |fs| {
                            p.ost.filesystem = fs.name.clone();

                            p.ost
                        })
                })
                .collect()
        }
    };

    let term = Term::stdout();

    tracing::debug!("Ost Pools: {:?}", xs);

    let x = xs.into_display_type(display_type);

    term.write_line(&x).unwrap();

    Ok(())
}

async fn ostpool_show(fsname: String, poolname: String) -> Result<(), ImlManagerCliError> {
    let mut pool = pool_lookup(&fsname, &poolname).await?;

    pool.ost.osts.sort_unstable();

    let mut table = Table::new();
    table.add_row(Row::from(&["Filesystem".to_string(), fsname]));
    table.add_row(Row::from(&["Name".to_string(), poolname]));
    table.add_row(Row::from(&["OSTs".to_string(), pool.ost.osts.join("\n")]));
    table.printstd();

    Ok(())
}

async fn ostpool_destroy(
    term: &Term,
    fsname: String,
    poolname: String,
) -> Result<(), ImlManagerCliError> {
    let pool = pool_lookup(&fsname, &poolname).await?;
    let resp = delete(&pool.resource_uri, "").await?;
    term.write_line(&format!("{} ost pool...", style("Destroying").green()))?;
    let objs: ObjCommands = resp.json().await?;
    wait_for_cmds_success(&objs.commands).await?;

    Ok(())
}

pub async fn ostpool_cli(command: OstPoolCommand) -> Result<(), ImlManagerCliError> {
    let term = Term::stdout();

    match command {
        OstPoolCommand::List {
            fsname,
            display_type,
        } => ostpool_list(fsname, display_type).await?,
        OstPoolCommand::Show { fsname, poolname } => ostpool_show(fsname, poolname).await?,
        OstPoolCommand::Create {
            fsname,
            poolname,
            osts,
        } => {
            let pool = OstPoolApi {
                ost: OstPool {
                    filesystem: fsname,
                    name: poolname,
                    osts,
                },
                ..Default::default()
            };
            let resp = post(OstPoolApi::endpoint_name(), pool).await?;

            term.write_line(&format!("{} ost pool...", style("Creating").green()))?;
            let objs: ObjCommand = resp.json().await?;
            wait_for_cmds_success(&[objs.command]).await?;
        }
        OstPoolCommand::Destroy { fsname, poolname } => {
            ostpool_destroy(&term, fsname, poolname).await?;
        }
        OstPoolCommand::Grow {
            fsname,
            poolname,
            osts,
        } => {
            let mut pool = pool_lookup(&fsname, &poolname).await?;
            let mut newlist = pool.ost.osts;
            newlist.extend(osts);
            newlist.sort();
            newlist.dedup();
            pool.ost.osts = newlist;

            tracing::debug!("POOL: {:?}", pool);
            term.write_line(&format!("{} ost pool...", style("Growing").green()))?;
            let uri = pool.resource_uri.clone();
            let resp = put(&uri, pool).await?;
            let objs: ObjCommand = resp.json().await?;
            wait_for_cmds_success(&[objs.command]).await?;
        }
        OstPoolCommand::Shrink {
            fsname,
            poolname,
            osts,
        } => {
            let mut pool = pool_lookup(&fsname, &poolname).await?;

            pool.ost.osts.retain(|o| !osts.contains(o));

            tracing::debug!("POOL: {:?}", pool);
            term.write_line(&format!("{} ost pool...", style("Shrinking").green()))?;
            let uri = pool.resource_uri.clone();
            let resp = put(&uri, pool).await?;

            let objs: ObjCommand = resp.json().await?;
            wait_for_cmds_success(&[objs.command]).await?;
        }
    };

    Ok(())
}
