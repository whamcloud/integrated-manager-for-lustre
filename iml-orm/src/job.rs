// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::{ChromaCoreCommandJob, ChromaCoreJob};
use crate::{
    schema::{chroma_core_command_jobs as cmdjobs, chroma_core_job as job},
    DbPool,
};
use diesel::{dsl, prelude::*};
use tokio_diesel::AsyncRunQueryDsl as _;

pub type WithCmd = dsl::Eq<cmdjobs::command_id, i32>;
pub type JobsByCmd = dsl::Select<dsl::Filter<cmdjobs::table, WithCmd>, cmdjobs::id>;

impl ChromaCoreCommandJob {
    pub fn with_cmd(id: i32) -> WithCmd {
        cmdjobs::command_id.eq(id)
    }
    pub fn jobs_by_cmd(id: i32) -> JobsByCmd {
        cmdjobs::table
            .filter(Self::with_cmd(id))
            .select(cmdjobs::id)
    }
}

pub type WithId = dsl::Eq<job::id, i32>;
pub type WithIds = dsl::EqAny<job::id, Vec<i32>>;
pub type ById = dsl::Filter<job::table, WithId>;
pub type ByIds = dsl::Filter<job::table, WithIds>;

impl ChromaCoreJob {
    pub fn with_id(id: i32) -> WithId {
        job::id.eq(id)
    }
    pub fn with_ids(ids: impl IntoIterator<Item = i32>) -> WithIds {
        let xs: Vec<_> = ids.into_iter().collect();

        job::id.eq_any(xs)
    }
    pub fn by_id(id: i32) -> ById {
        job::table.filter(Self::with_id(id))
    }
    pub fn by_ids(id: impl IntoIterator<Item = i32>) -> ByIds {
        job::table.filter(Self::with_ids(id))
    }
}

pub async fn get_jobs_by_cmd(
    id: i32,
    pool: &DbPool,
) -> Result<Vec<ChromaCoreJob>, tokio_diesel::AsyncError> {
    let jobs: Vec<i32> = ChromaCoreCommandJob::jobs_by_cmd(id)
        .get_results_async(&pool)
        .await?;

    ChromaCoreJob::by_ids(jobs).get_results_async(&pool).await
}
