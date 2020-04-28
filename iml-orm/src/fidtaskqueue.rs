// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreFidtaskqueue;
use crate::{
    diesel::ExpressionMethods, lustrefid::LustreFid, schema::chroma_core_fidtaskqueue as fidq,
    task::ChromaCoreTask, Executable,
};
use diesel::{dsl, prelude::*};
use serde_json;

pub type Table = fidq::table;
pub type WithFid = dsl::Eq<fidq::fid, LustreFid>;
pub type ByFid = dsl::Filter<fidq::table, WithFid>;

impl ChromaCoreFidtaskqueue {
    pub fn with_fid(fid: LustreFid) -> WithFid {
        fidq::fid.eq(fid)
    }
    pub fn by_fid(fid: LustreFid) -> ByFid {
        fidq::table.filter(Self::with_fid(fid))
    }
}

pub fn insert_fidtask(
    fid: LustreFid,
    data: serde_json::Value,
    task: &ChromaCoreTask,
) -> impl Executable {
    diesel::insert_into(fidq::table).values((
        fidq::fid.eq(fid),
        fidq::data.eq(data),
        fidq::task_id.eq(task.id),
    ))
}
