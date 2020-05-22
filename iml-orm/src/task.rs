// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreTask;
use crate::schema::chroma_core_task as task;
use diesel::{
    backend::Backend,
    dsl,
    prelude::*,
    serialize::{self, Output, ToSql},
    sql_types,
};
use std::{fmt, io::Write};

pub type Table = task::table;
pub type WithName = dsl::Eq<task::name, String>;
pub type WithFs = dsl::Eq<task::filesystem_id, i32>;
pub type WithOutState = dsl::NotEq<task::state, String>;
pub type ByName = dsl::Filter<task::table, WithName>;
pub type OutgestHost = dsl::Filter<
    task::table,
    dsl::And<
        WithOutState,
        dsl::And<
            WithFs,
            dsl::Or<dsl::IsNull<task::running_on_id>, dsl::Eq<task::running_on_id, i32>>,
        >,
    >,
>;

#[derive(Debug, Clone, Copy)]
pub enum TaskState {
    Started,
    Finished,
    Closed,
}

impl<DB> ToSql<sql_types::Text, DB> for TaskState
where
    DB: Backend,
    str: ToSql<sql_types::Text, DB>,
{
    fn to_sql<W: Write>(&self, out: &mut Output<W, DB>) -> serialize::Result {
        (self.to_string().as_str() as &str).to_sql(out)
    }
}

impl fmt::Display for TaskState {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TaskState::Started => write!(f, "started"),
            TaskState::Finished => write!(f, "finished"),
            TaskState::Closed => write!(f, "closed"),
        }
    }
}

impl ChromaCoreTask {
    pub fn all() -> Table {
        task::table
    }
    pub fn with_name(name: impl ToString) -> WithName {
        task::name.eq(name.to_string())
    }
    pub fn with_fs(fs_id: i32) -> WithFs {
        task::filesystem_id.eq(fs_id)
    }
    pub fn without_state(state: TaskState) -> WithOutState {
        task::state.ne(state.to_string())
    }
    pub fn by_name(name: impl ToString) -> ByName {
        task::table.filter(Self::with_name(name))
    }
    pub fn outgestable(fs_id: i32, host_id: i32) -> OutgestHost {
        task::table.filter(
            Self::without_state(TaskState::Closed).and(
                Self::with_fs(fs_id).and(
                    task::running_on_id
                        .is_null()
                        .or(task::running_on_id.eq(host_id)),
                ),
            ),
        )
    }
}
