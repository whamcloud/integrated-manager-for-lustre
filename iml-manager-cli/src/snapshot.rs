// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{api_utils::graphql, error::ImlManagerCliError};
use console::Term;
use iml_command_utils::{
    display_utils::{DisplayType, IntoDisplayType as _},
    wait_for_cmds_success,
};
use iml_graphql_queries::snapshot as snapshot_queries;
use iml_wire_types::snapshot;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum IntervalCommand {
    /// List snapshots intervals
    List {
        /// Set the display type
        ///
        /// The display type can be one of the following:
        /// tabular: display content in a table format
        /// json: return data in json format
        /// yaml: return data in yaml format
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
        // TODO? Optional FS?
    },
    /// Add new snapshot interval
    Add {
        /// Use barrier when creating snapshots
        #[structopt(short = "b", long = "barrier")]
        barrier: bool,
        /// Filesystem to add a snapshot interval for
        filesystem: String,
        /// Snapshot interval in human form, e. g. 1 hour
        #[structopt(required = true, min_values = 1)]
        interval: Vec<String>,
    },
    /// Remove snapshot intervals
    Remove {
        /// The ids of the snapshot interval to remove
        #[structopt(required = true, min_values = 1)]
        ids: Vec<u32>,
    },
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
        /// Set the display type
        ///
        /// The display type can be one of the following:
        /// tabular: display content in a table format
        /// json: return data in json format
        /// yaml: return data in yaml format
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
        /// The filesystem to list snapshots for
        fsname: String,
    },
    /// Snapshot intervals operations
    Interval(IntervalCommand),
}

async fn interval_cli(cmd: IntervalCommand) -> Result<(), ImlManagerCliError> {
    match cmd {
        IntervalCommand::List { display_type } => {
            let query = snapshot_queries::list_intervals::build();

            let resp: iml_graphql_queries::Response<snapshot_queries::list_intervals::Resp> =
                graphql(query).await?;
            let intervals = Result::from(resp)?.data.snapshot_intervals;

            let x = intervals.into_display_type(display_type);

            let term = Term::stdout();
            term.write_line(&x).unwrap();

            Ok(())
        }
        IntervalCommand::Add {
            filesystem,
            interval,
            barrier,
        } => {
            let query = snapshot_queries::create_interval::build(
                filesystem,
                interval.join(" "),
                Some(barrier),
            );

            let _resp: iml_graphql_queries::Response<snapshot_queries::create_interval::Resp> =
                graphql(query).await?;

            Ok(())
        }
        IntervalCommand::Remove { ids } => {
            for id in ids {
                let query = snapshot_queries::remove_interval::build(id);

                let _resp: iml_graphql_queries::Response<snapshot_queries::remove_interval::Resp> =
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
            let snaps = Result::from(resp)?.data.snapshots;

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
            let x = Result::from(resp)?.data.create_snapshot;
            wait_for_cmds_success(&[x]).await?;

            Ok(())
        }
        SnapshotCommand::Destroy(x) => {
            let query = snapshot_queries::destroy::build(x.fsname, x.name, x.force);

            let resp: iml_graphql_queries::Response<snapshot_queries::destroy::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.destroy_snapshot;
            wait_for_cmds_success(&[x]).await?;

            Ok(())
        }
        SnapshotCommand::Mount(x) => {
            let query = snapshot_queries::mount::build(x.fsname, x.name);
            let resp: iml_graphql_queries::Response<snapshot_queries::mount::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.mount_snapshot;
            wait_for_cmds_success(&[x]).await?;

            Ok(())
        }
        SnapshotCommand::Unmount(x) => {
            let query = snapshot_queries::unmount::build(x.fsname, x.name);
            let resp: iml_graphql_queries::Response<snapshot_queries::unmount::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.unmount_snapshot;
            wait_for_cmds_success(&[x]).await?;

            Ok(())
        }
        SnapshotCommand::Interval(cmd) => interval_cli(cmd).await,
    }
}
