// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::graphql,
    display_utils::{wrap_fut, DisplayType, IntoDisplayType as _},
    error::EmfManagerCliError,
};
use console::{style, Term};
use emf_graphql_queries::ostpool as ostpool_queries;
use emf_wire_types::{Command, OstPoolGraphql};
use prettytable::{Row, Table};
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

async fn get_pool(fsname: &str, poolname: &str) -> Result<OstPoolGraphql, EmfManagerCliError> {
    let query = ostpool_queries::list::build(Some(fsname.into()), Some(poolname.into()));
    let resp: emf_graphql_queries::Response<ostpool_queries::list::Resp> =
        wrap_fut("Fetching OstPools...", graphql(query)).await?;
    let xs: Vec<OstPoolGraphql> = Result::from(resp)?.data.ost_pool.list;

    xs.into_iter().next().ok_or_else(|| {
        EmfManagerCliError::DoesNotExist(format!(
            "Ostpool fs name:{}, pool name: {}",
            fsname, poolname
        ))
    })
}

async fn ostpool_list(
    fsname: Option<String>,
    display_type: DisplayType,
) -> Result<(), EmfManagerCliError> {
    let query = ostpool_queries::list::build(fsname, None);
    let resp: emf_graphql_queries::Response<ostpool_queries::list::Resp> =
        wrap_fut("Fetching OstPools...", graphql(query)).await?;
    let xs: Vec<OstPoolGraphql> = Result::from(resp)?.data.ost_pool.list;

    let term = Term::stdout();

    tracing::debug!("Ost Pools: {:?}", xs);

    let x = xs.into_display_type(display_type);

    term.write_line(&x).unwrap();

    Ok(())
}

async fn ostpool_show(fsname: String, poolname: String) -> Result<(), EmfManagerCliError> {
    let mut pool = get_pool(&fsname, &poolname).await?;

    pool.osts.sort_unstable();

    let mut table = Table::new();
    table.add_row(Row::from(&["Filesystem".to_string(), fsname]));
    table.add_row(Row::from(&["Name".to_string(), poolname]));
    table.add_row(Row::from(&["OSTs".to_string(), pool.osts.join("\n")]));
    table.printstd();

    Ok(())
}

async fn ostpool_destroy(
    term: &Term,
    fsname: String,
    poolname: String,
) -> Result<(), EmfManagerCliError> {
    let pool = get_pool(&fsname, &poolname).await?;

    term.write_line(&format!("{} ost pool...", style("Destroying").green()))?;

    todo!();
}

pub async fn ostpool_cli(command: OstPoolCommand) -> Result<(), EmfManagerCliError> {
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
            todo!();
        }
        OstPoolCommand::Destroy { fsname, poolname } => {
            ostpool_destroy(&term, fsname, poolname).await?;
        }
        OstPoolCommand::Grow {
            fsname,
            poolname,
            osts,
        } => {
            let mut pool = get_pool(&fsname, &poolname).await?;
            let mut newlist = pool.osts;
            newlist.extend(osts);
            newlist.sort();
            newlist.dedup();
            pool.osts = newlist;

            tracing::debug!("POOL: {:?}", pool);
            term.write_line(&format!("{} ost pool...", style("Growing").green()))?;

            todo!();
        }
        OstPoolCommand::Shrink {
            fsname,
            poolname,
            osts,
        } => {
            let mut pool = get_pool(&fsname, &poolname).await?;

            pool.osts.retain(|o| !osts.contains(o));

            tracing::debug!("POOL: {:?}", pool);
            term.write_line(&format!("{} ost pool...", style("Shrinking").green()))?;

            todo!();
        }
    };

    Ok(())
}
