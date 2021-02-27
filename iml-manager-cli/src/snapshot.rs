// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::graphql,
    api_utils::wait_for_cmds_success,
    display_utils::{DisplayType, IntoDisplayType as _},
    error::ImlManagerCliError,
};
use console::Term;
use iml_graphql_queries::snapshot as snapshot_queries;
use iml_wire_types::snapshot;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum PolicyCommand {
    /// List snapshot policies (default)
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
    /// Create or update snapshot policy
    Create {
        /// Filesystem to create a snapshot policy for
        filesystem: String,
        /// Automatic snapshot interval in human form, e. g. 1hour
        #[structopt()]
        interval: String,
        /// Time to start making automatic snapshots, e. g. 2020-12-25T20:00:00Z
        #[structopt(short = "s", long = "start")]
        start: Option<String>,
        /// Use barrier when creating snapshots
        #[structopt(short = "b", long = "barrier")]
        barrier: bool,
        /// Maximum number of snapshots
        #[structopt(short = "k", long = "keep")]
        keep: i32,
        /// The number of days when keep the most recent snapshot of each day
        #[structopt(short = "d", long = "daily")]
        daily: Option<i32>,
        /// The number of weeks when keep the most recent snapshot of each week
        #[structopt(short = "w", long = "weekly")]
        weekly: Option<i32>,
        /// The number of months when keep the most recent snapshot of each month
        #[structopt(short = "m", long = "monthly")]
        monthly: Option<i32>,
    },
    /// Remove snapshot policies
    Remove {
        /// Filesystem names to remove policies for
        #[structopt(required = true, min_values = 1)]
        filesystem: Vec<String>,
    },
}

impl Default for PolicyCommand {
    fn default() -> Self {
        PolicyCommand::List {
            display_type: DisplayType::Tabular,
        }
    }
}

#[derive(Debug, StructOpt)]
pub enum SnapshotCommand {
    /// Create a snapshot
    Create(snapshot::Create),
    /// Destroy the snapshot
    Destroy(snapshot::Destroy),
    /// Mount a snapshot
    Mount(snapshot::Mount),
    /// Unmount a snapshot
    Unmount(snapshot::Unmount),
    /// List snapshots
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
        /// The filesystem to list snapshots for
        fsname: String,
    },
    /// Automatic snapshot policies operations
    Policy {
        #[structopt(subcommand)]
        command: Option<PolicyCommand>,
    },
}

async fn policy_cli(cmd: PolicyCommand) -> Result<(), ImlManagerCliError> {
    match cmd {
        PolicyCommand::List { display_type } => {
            let query = snapshot_queries::policy::list::build();

            let resp: iml_graphql_queries::Response<snapshot_queries::policy::list::Resp> =
                graphql(query).await?;
            let policies = Result::from(resp)?.data.snapshot.policies;

            let x = policies.into_display_type(display_type);

            let term = Term::stdout();
            term.write_line(&x).unwrap();

            Ok(())
        }
        PolicyCommand::Create {
            filesystem,
            interval,
            start,
            barrier,
            keep,
            daily,
            weekly,
            monthly,
        } => {
            let query =
                snapshot_queries::policy::create::build(snapshot_queries::policy::create::Vars {
                    filesystem,
                    interval,
                    start,
                    barrier: Some(barrier),
                    keep,
                    daily,
                    weekly,
                    monthly,
                });

            let _resp: iml_graphql_queries::Response<snapshot_queries::policy::create::Resp> =
                graphql(query).await?;

            Ok(())
        }
        PolicyCommand::Remove { filesystem } => {
            for fs in filesystem {
                let query = snapshot_queries::policy::remove::build(fs);

                let _resp: iml_graphql_queries::Response<snapshot_queries::policy::remove::Resp> =
                    graphql(query).await?;
            }

            Ok(())
        }
    }
}

pub async fn snapshot_cli(command: SnapshotCommand) -> Result<(), ImlManagerCliError> {
    match command {
        SnapshotCommand::List {
            display_type,
            fsname,
        } => {
            let query = snapshot_queries::list::build(fsname, None, None, None, Some(1_000));
            let resp: iml_graphql_queries::Response<snapshot_queries::list::Resp> =
                graphql(query).await?;
            let snaps = Result::from(resp)?.data.snapshot.snapshots;

            let x = snaps.into_display_type(display_type);

            let term = Term::stdout();
            term.write_line(&x).unwrap();

            Ok(())
        }
        SnapshotCommand::Create(x) => {
            let query =
                snapshot_queries::create::build(x.fsname, x.name, x.comment, Some(x.use_barrier));

            let resp: iml_graphql_queries::Response<snapshot_queries::create::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.snapshot.create;
            wait_for_cmds_success(&[x]).await?;

            Ok(())
        }
        SnapshotCommand::Destroy(x) => {
            let query = snapshot_queries::destroy::build(x.fsname, x.name, x.force);

            let resp: iml_graphql_queries::Response<snapshot_queries::destroy::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.snapshot.destroy;
            wait_for_cmds_success(&[x]).await?;

            Ok(())
        }
        SnapshotCommand::Mount(x) => {
            let query = snapshot_queries::mount::build(x.fsname, x.name);
            let resp: iml_graphql_queries::Response<snapshot_queries::mount::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.snapshot.mount;
            wait_for_cmds_success(&[x]).await?;

            Ok(())
        }
        SnapshotCommand::Unmount(x) => {
            let query = snapshot_queries::unmount::build(x.fsname, x.name);
            let resp: iml_graphql_queries::Response<snapshot_queries::unmount::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.snapshot.unmount;
            wait_for_cmds_success(&[x]).await?;

            Ok(())
        }
        SnapshotCommand::Policy { command } => policy_cli(command.unwrap_or_default()).await,
    }
}
