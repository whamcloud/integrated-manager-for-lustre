// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::graphql,
    display_utils::{DisplayType, IntoDisplayType as _},
    error::EmfManagerCliError,
};
use console::Term;
use emf_graphql_queries::snapshot as snapshot_queries;
use emf_wire_types::snapshot;
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
pub enum IntervalCommand {
    /// List snapshots intervals
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
    /// Add new snapshot interval
    Add {
        /// Use barrier when creating snapshots
        #[structopt(short = "b", long = "barrier")]
        barrier: bool,
        /// Filesystem to add a snapshot interval for
        filesystem: String,
        /// Snapshot interval in human form, e. g. 1hour
        #[structopt(required = true, min_values = 1)]
        interval: Vec<String>,
    },
    /// Remove snapshot intervals
    Remove {
        /// The ids of the snapshot intervals to remove
        #[structopt(required = true, min_values = 1)]
        ids: Vec<i32>,
    },
}

#[derive(Debug, StructOpt)]
pub enum RetentionCommand {
    /// List snapshots retention rules
    List {
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
    },
    /// Create snapshot retention rule
    Create {
        /// Filesystem to create a snapshot retention rule for
        filesystem: String,
        /// Delete the oldest snapshot when available space falls below this value
        reserve_value: u32,
        /// The unit of measurement associated with the reserve_value (%, GiB or TiB)
        reserve_unit: snapshot::ReserveUnit,
        /// Minimum number of snapshots to keep (default: 0)
        keep_num: Option<u32>,
    },
    /// Remove snapshot retention rule
    Remove {
        /// The ids of the retention rules to remove
        #[structopt(required = true, min_values = 1)]
        ids: Vec<i32>,
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
        /// Display type: json, yaml, tabular
        #[structopt(short = "d", long = "display", default_value = "tabular")]
        display_type: DisplayType,
        /// The filesystem to list snapshots for
        fsname: String,
    },
    /// Snapshot intervals operations
    Interval(IntervalCommand),
    /// Snapshot retention rules operations
    Retention(RetentionCommand),
}

async fn interval_cli(cmd: IntervalCommand) -> Result<(), EmfManagerCliError> {
    match cmd {
        IntervalCommand::List { display_type } => {
            let query = snapshot_queries::list_intervals::build();

            let resp: emf_graphql_queries::Response<snapshot_queries::list_intervals::Resp> =
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

            let _resp: emf_graphql_queries::Response<snapshot_queries::create_interval::Resp> =
                graphql(query).await?;

            Ok(())
        }
        IntervalCommand::Remove { ids } => {
            for id in ids {
                let query = snapshot_queries::remove_interval::build(id);

                let _resp: emf_graphql_queries::Response<snapshot_queries::remove_interval::Resp> =
                    graphql(query).await?;
            }
            Ok(())
        }
    }
}

async fn retention_cli(cmd: RetentionCommand) -> Result<(), EmfManagerCliError> {
    match cmd {
        RetentionCommand::List { display_type } => {
            let query = snapshot_queries::list_retentions::build();

            let resp: emf_graphql_queries::Response<snapshot_queries::list_retentions::Resp> =
                graphql(query).await?;
            let retentions = Result::from(resp)?.data.snapshot_retention_policies;

            let x = retentions.into_display_type(display_type);

            let term = Term::stdout();
            term.write_line(&x).unwrap();

            Ok(())
        }
        RetentionCommand::Create {
            filesystem,
            keep_num,
            reserve_value,
            reserve_unit,
        } => {
            let query = snapshot_queries::create_retention::build(
                filesystem,
                reserve_value,
                reserve_unit,
                keep_num,
            );

            let _resp: emf_graphql_queries::Response<snapshot_queries::create_retention::Resp> =
                graphql(query).await?;

            Ok(())
        }
        RetentionCommand::Remove { ids } => {
            for id in ids {
                let query = snapshot_queries::remove_retention::build(id);

                let _resp: emf_graphql_queries::Response<snapshot_queries::remove_retention::Resp> =
                    graphql(query).await?;
            }
            Ok(())
        }
    }
}

pub async fn snapshot_cli(command: SnapshotCommand) -> Result<(), EmfManagerCliError> {
    match command {
        SnapshotCommand::List {
            display_type,
            fsname,
        } => {
            let query = snapshot_queries::list::build(fsname, None, None, None, Some(1_000));
            let resp: emf_graphql_queries::Response<snapshot_queries::list::Resp> =
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

            let resp: emf_graphql_queries::Response<snapshot_queries::create::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.create_snapshot;

            unimplemented!();

            Ok(())
        }
        SnapshotCommand::Destroy(x) => {
            let query = snapshot_queries::destroy::build(x.fsname, x.name, x.force);

            let resp: emf_graphql_queries::Response<snapshot_queries::destroy::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.destroy_snapshot;

            unimplemented!();

            Ok(())
        }
        SnapshotCommand::Mount(x) => {
            let query = snapshot_queries::mount::build(x.fsname, x.name);
            let resp: emf_graphql_queries::Response<snapshot_queries::mount::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.mount_snapshot;

            unimplemented!();

            Ok(())
        }
        SnapshotCommand::Unmount(x) => {
            let query = snapshot_queries::unmount::build(x.fsname, x.name);
            let resp: emf_graphql_queries::Response<snapshot_queries::unmount::Resp> =
                graphql(query).await?;
            let x = Result::from(resp)?.data.unmount_snapshot;

            unimplemented!();

            Ok(())
        }
        SnapshotCommand::Interval(cmd) => interval_cli(cmd).await,
        SnapshotCommand::Retention(cmd) => retention_cli(cmd).await,
    }
}
