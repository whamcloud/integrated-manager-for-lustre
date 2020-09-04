// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::graphql,
    display_utils::{DisplayType, IntoDisplayType as _},
    error::ImlManagerCliError,
};
use console::Term;
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

        fsname: String,
    },
}

async fn list(fsname: String) -> Result<Vec<snapshot::Snapshot>, ImlManagerCliError> {
    let query = format!(
        r#"
{{
  snapshots(fsname: "{}") {{
    comment
    create_time: createTime
    filesystem_name: filesystemName
    modify_time: modifyTime
    mounted
    snapshot_fsname: snapshotFsname
    snapshot_name: snapshotName
  }}
}}
            "#,
        fsname
    );
    let resp = graphql(query).await?;

    serde_json::from_value(resp.get("data").unwrap().get("snapshots").unwrap().clone())
        .map_err(|e| e.into())
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
        _ => panic!("Not implemented"),
    }
}
