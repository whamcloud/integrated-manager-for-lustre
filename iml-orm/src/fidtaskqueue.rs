// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreFidtaskqueue;
use crate::{lustrefid::LustreFid, schema::chroma_core_fidtaskqueue, task::ChromaCoreTask, DbPool};
use serde_json;
use tokio_diesel::AsyncRunQueryDsl as _;

pub type Table = chroma_core_fidtaskqueue::table;

#[derive(Insertable)]
#[cfg_attr(feature = "postgres-interop", table_name = "chroma_core_fidtaskqueue")]
pub struct NewFidTask {
    pub fid: LustreFid,
    pub data: serde_json::Value,
    pub task_id: i32,
}

pub async fn insert(
    fid: LustreFid,
    data: serde_json::Value,
    task: &ChromaCoreTask,
    pool: &DbPool,
) -> Result<(), tokio_diesel::AsyncError> {
    diesel::insert_into(chroma_core_fidtaskqueue::table)
        .values(NewFidTask {
            fid,
            data,
            task_id: task.id,
        })
        .execute_async(pool)
        .await?;
    Ok(())
}
