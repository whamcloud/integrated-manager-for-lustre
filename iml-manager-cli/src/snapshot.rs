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
}

async fn list(fsname: String) -> Result<Vec<snapshot::Snapshot>, ImlManagerCliError> {
    let query = snapshot_queries::list::build(fsname, None, None, None, Some(1_000));

    let resp: iml_graphql_queries::Response<snapshot_queries::list::Resp> = graphql(query).await?;
    let x = Result::from(resp)?.data.snapshots;

    Ok(x)
}

pub async fn snapshot_cli(command: SnapshotCommand) -> Result<(), ImlManagerCliError> {
    match command {
        SnapshotCommand::List {
            display_type,
            fsname,
        } => {
            let snaps = list(fsname).await?;

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
    }
}
