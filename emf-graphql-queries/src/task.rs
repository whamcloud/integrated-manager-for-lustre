// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Resp<T> {
    pub task: T,
}

pub mod create {
    use crate::Query;
    use emf_wire_types::{task::TaskArgs, Command};

    pub static QUERY: &str = r#"
            mutation CreateTask($fsname: String!, $task: TaskArgs!) {
              task {
                create(fsname: $fsname, taskArgs: $task) {
                  task_id: taskId
                  command {
                    id
                    cancelled
                    complete
                    created_at: createdAt
                    errored
                    id
                    jobs
                    logs
                    message
                    resource_uri: resourceUri
                  }
                }
              }
            }
        "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        fsname: String,
        task: TaskArgs,
    }

    pub fn build(fsname: impl ToString, task: TaskArgs) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                task,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct TaskCommand {
        task_id: i32,
        command: Command,
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Create {
        pub create: TaskCommand,
    }

    pub type Resp = super::Resp<Create>;
}

pub mod remove {
    use emf_wire_types::Command;

    use crate::Query;

    pub static QUERY: &str = r#"
        mutation RemoveTask($task_id: Int!) {
          task {
            remove(taskId: $task_id) {
              id
              cancelled
              complete
              created_at: createdAt
              errored
              id
              jobs
              logs
              message
              resource_uri: resourceUri
            }
          }
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        task_id: i32,
    }

    pub fn build(task_id: i32) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars { task_id }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Remove {
        remove: Command,
    }

    pub type Resp = super::Resp<Remove>;
}

pub mod list {
    use crate::Query;
    use emf_wire_types::task::TaskOut;

    pub static QUERY: &str = r#"
        query List {
          task {
            list {
              id
              name
              start
              finish
              state
              fids_total: fidsTotal
              fids_completed: fidsCompleted
              fids_failed: fidsFailed
              data_transfered: dataTransfered
              single_runner: singleRunner
              keep_failed: keepFailed
              actions
              args {
                key
                value
              }
              filesystem_id: filesystemId
              running_on_id: runningOnId
            }
          }
        }
    "#;

    pub fn build() -> Query<()> {
        Query {
            query: QUERY.to_string(),
            variables: None,
        }
    }

    pub struct List {
        pub list: Vec<TaskOut>,
    }

    pub type Resp = super::Resp<TaskOut>;
}
