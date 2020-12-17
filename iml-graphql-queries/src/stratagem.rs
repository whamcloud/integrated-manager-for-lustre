// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Resp<T> {
    pub stratagem: T,
}

pub mod list_reports {
    use crate::Query;
    use iml_wire_types::StratagemReport;

    pub static QUERY: &str = r#"
        query StratagemReports {
          stratagem {
            stratagemReports {
              filename
              size
              modify_time: modifyTime
            }
          }
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {}

    pub fn build() -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: None,
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct StratagemReports {
        #[serde(rename(deserialize = "stratagemReports"))]
        pub stratagem_reports: Vec<StratagemReport>,
    }

    pub type Resp = super::Resp<StratagemReports>;
}

pub mod delete_report {
    use crate::Query;

    pub static QUERY: &str = r#"
        mutation DeleteStratagemReport($filename: String!) {
          stratagem {
            deleteStratagemReport(filename: $filename)
          }
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        filename: String,
    }

    pub fn build(filename: impl ToString) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                filename: filename.to_string(),
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct DeleteStratagemReport {
        #[serde(rename(deserialize = "deleteStratagemReport"))]
        pub delete_stratagem_report: bool,
    }

    pub type Resp = super::Resp<DeleteStratagemReport>;
}

pub mod run_stratagem {
    use iml_wire_types::{stratagem::StratagemGroup, task::TaskArgs, Command};

    use crate::Query;

    pub static QUERY: &str = r#"
        mutation runStratagem($uuid: String!, $fsname: String!, $tasks: [TaskArgs!]!, $groups: [StratagemGroup!]!) {
          stratagem {
            runStratagem(uuid: $uuid, fsname: $fsname, tasks: $tasks, groups: $groups) {
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
        uuid: String,
        fsname: String,
        tasks: Vec<TaskArgs>,
        groups: Vec<StratagemGroup>,
    }

    pub fn build(
        uuid: impl ToString,
        fsname: impl ToString,
        tasks: Vec<TaskArgs>,
        groups: Vec<StratagemGroup>,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                uuid: uuid.to_string(),
                fsname: fsname.to_string(),
                tasks,
                groups,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct RunStratagem {
        #[serde(rename(deserialize = "runStratagem"))]
        pub run_stratagem: Command,
    }

    pub type Resp = super::Resp<RunStratagem>;
}

pub mod fast_file_scan {
    use iml_wire_types::Command;

    use crate::Query;

    pub static QUERY: &str = r#"
        mutation RunFastFileScan($fsname: String!, $report_duration: Duration, $purge_duration: Duration) {
          stratagem {
            runFastFileScan(fsname: $fsname, reportDuration: $report_duration, purgeDuration: $purge_duration) {
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
        fsname: String,
        report_duration: Option<String>,
        purge_duration: Option<String>,
    }

    pub fn build(
        fsname: impl ToString,
        report_duration: Option<String>,
        purge_duration: Option<String>,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                report_duration,
                purge_duration,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct RunFastFileScan {
        #[serde(rename(deserialize = "runFastFileScan"))]
        pub run_fast_file_scan: Command,
    }

    pub type Resp = super::Resp<RunFastFileScan>;
}

pub mod task_fidlist {
    use iml_wire_types::Command;

    use crate::Query;

    pub static QUERY: &str = r#"
        mutation RunTaskFidlist($jobname: String!, $taskname: String!, $fsname: String!, $task_args: String!, $fidlist: [String!]!) {
          stratagem {
            runTaskFidlist(jobname: $jobname, taskname: $taskname, fsname: $fsname, task_args: $task_args, fidlist: $fidlist) {
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
	jobname: String,
	taskname: String,
        fsname: String,
	task_args: String,
	fidlist: Vec<String>,
    }

    pub fn build(
	jobname: impl ToString,
	taskname: impl ToString,
        fsname: impl ToString,
	task_args: impl ToString,
	fidlist: Vec<String>,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
		jobname: jobname.to_string(),
		taskname: taskname.to_string(),
                fsname: fsname.to_string(),
		task_args: task_args.to_string(),
		fidlist,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct RunTaskFidlist {
        #[serde(rename(deserialize = "runTaskFidlist"))]
        pub run_taskFidlist: Command,
    }

    pub type Resp = super::Resp<RunTaskFidlist>;
}

pub mod filesync {
    use iml_wire_types::Command;

    use crate::Query;

    pub static QUERY: &str = r#"
        mutation RunFilesync($fsname: String!, $remote: String!, $expression: String!, $action: String!) {
          stratagem {
            runFilesync(fsname: $fsname, remote: $remote, expression: $expression, action: $action) {
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
        fsname: String,
        remote: String,
        expression: String,
        action: String,
    }

    pub fn build(
        fsname: impl ToString,
        remote: impl ToString,
        expression: impl ToString,
        action: impl ToString,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                remote: remote.to_string(),
                expression: expression.to_string(),
                action: action.to_string(),
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct RunFilesync {
        #[serde(rename(deserialize = "runFilesync"))]
        pub run_filesync: Command,
    }

    pub type Resp = super::Resp<RunFilesync>;
}

pub mod cloudsync {
    use iml_wire_types::Command;

    use crate::Query;

    pub static QUERY: &str = r#"
        mutation RunCloudsync($fsname: String!, $remote: String!, $expression: String!, $action: String!) {
          stratagem {
            runCloudsync(fsname: $fsname, remote: $remote, expression: $expression, action: $action) {
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
        fsname: String,
        remote: String,
        expression: String,
        action: String,
    }

    pub fn build(
        fsname: impl ToString,
        remote: impl ToString,
        expression: impl ToString,
        action: impl ToString,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                remote: remote.to_string(),
                expression: expression.to_string(),
                action: action.to_string(),
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct RunCloudsync {
        #[serde(rename(deserialize = "runCloudsync"))]
        pub run_cloudsync: Command,
    }

    pub type Resp = super::Resp<RunCloudsync>;
}
