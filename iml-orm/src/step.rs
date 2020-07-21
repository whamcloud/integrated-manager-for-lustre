// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreStepresult;
use crate::schema::chroma_core_stepresult as step;
use diesel::{dsl, prelude::*};

pub type WithJobs = dsl::EqAny<step::job_id, Vec<i32>>;
pub type ByJobs = dsl::Order<dsl::Filter<step::table, WithJobs>, step::modified_at>;

impl ChromaCoreStepresult {
    pub fn with_jobs(ids: impl IntoIterator<Item = i32>) -> WithJobs {
        let ids: Vec<i32> = ids.into_iter().collect();

        step::job_id.eq_any(ids)
    }
    pub fn by_jobs(ids: impl IntoIterator<Item = i32>) -> ByJobs {
        step::table
            .filter(Self::with_jobs(ids))
            .order(step::modified_at)
    }
}
