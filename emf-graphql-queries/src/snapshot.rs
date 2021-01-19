// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod create {
    use crate::Query;
    use emf_wire_types::Command;

    pub static QUERY: &str = r#"
            mutation CreateSnapshot($fsname: String!, $name: String!, $comment: String, $use_barrier: Boolean) {
              createSnapshot(fsname: $fsname, name: $name, comment: $comment, useBarrier: $use_barrier) {
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
        "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        fsname: String,
        name: String,
        comment: Option<String>,
        use_barrier: Option<bool>,
    }

    pub fn build(
        fsname: impl ToString,
        name: impl ToString,
        comment: Option<impl ToString>,
        use_barrier: Option<bool>,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                name: name.to_string(),
                comment: comment.map(|x| x.to_string()),
                use_barrier,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "createSnapshot"))]
        pub create_snapshot: Command,
    }
}

pub mod destroy {
    use crate::Query;
    use emf_wire_types::Command;

    pub static QUERY: &str = r#"
        mutation DestroySnapshot($fsname: String!, $name: String!, $force: Boolean!) {
            destroySnapshot(fsname: $fsname, name: $name, force: $force) {
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
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        fsname: String,
        name: String,
        force: bool,
    }

    pub fn build(fsname: impl ToString, name: impl ToString, force: bool) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                name: name.to_string(),
                force,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "destroySnapshot"))]
        pub destroy_snapshot: Command,
    }
}

pub mod mount {
    use crate::Query;
    use emf_wire_types::Command;

    pub static QUERY: &str = r#"
        mutation MountSnapshot($fsname: String!, $name: String!) {
          mountSnapshot(fsname: $fsname, name: $name) {
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
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        fsname: String,
        name: String,
    }

    pub fn build(fsname: impl ToString, name: impl ToString) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                name: name.to_string(),
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "mountSnapshot"))]
        pub mount_snapshot: Command,
    }
}

pub mod unmount {
    use crate::Query;
    use emf_wire_types::Command;

    pub static QUERY: &str = r#"
        mutation UnmountSnapshot($fsname: String!, $name: String!) {
          unmountSnapshot(fsname: $fsname, name: $name) {
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
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        fsname: String,
        name: String,
    }

    pub fn build(fsname: impl ToString, name: impl ToString) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                name: name.to_string(),
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "unmountSnapshot"))]
        pub unmount_snapshot: Command,
    }
}

pub mod list {
    use crate::Query;
    use emf_wire_types::{snapshot::Snapshot, SortDir};

    pub static QUERY: &str = r#"
        query Snapshots($fsname: String!, $name: String, $dir: SortDir, $offset: Int, $limit: Int) {
          snapshots(fsname: $fsname, name: $name, dir: $dir, offset: $offset, limit: $limit) {
            comment
            create_time: createTime
            filesystem_name: filesystemName
            modify_time: modifyTime
            mounted
            snapshot_fsname: snapshotFsname
            snapshot_name: snapshotName
          }
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        fsname: String,
        name: Option<String>,
        dir: Option<SortDir>,
        offset: Option<u32>,
        limit: Option<u32>,
    }

    pub fn build(
        fsname: impl ToString,
        name: Option<&str>,
        dir: Option<SortDir>,
        offset: Option<u32>,
        limit: Option<u32>,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                name: name.map(|x| x.to_string()),
                dir,
                offset,
                limit,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "snapshots"))]
        pub snapshots: Vec<Snapshot>,
    }
}

pub mod create_interval {
    use crate::Query;

    pub static QUERY: &str = r#"
        mutation CreateSnapshotInterval($fsname: String!, $interval: Duration!, $use_barrier: Boolean) {
            createSnapshotInterval(fsname: $fsname, interval: $interval, useBarrier: $use_barrier)
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        fsname: String,
        interval: String,
        use_barrier: Option<bool>,
    }

    pub fn build(
        fsname: impl ToString,
        interval: String,
        use_barrier: Option<bool>,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                interval,
                use_barrier,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "createSnapshotInterval"))]
        pub create_snapshot_interval: bool,
    }
}

pub mod remove_interval {
    use crate::Query;

    pub static QUERY: &str = r#"
        mutation RemoveSnapshotInterval($id: Int!) {
          removeSnapshotInterval(id: $id)
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        id: i32,
    }

    pub fn build(id: i32) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars { id }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "removeSnapshotInterval"))]
        pub remove_snapshot_interval: bool,
    }
}

pub mod list_intervals {
    use crate::Query;
    use emf_wire_types::snapshot::SnapshotInterval;

    pub static QUERY: &str = r#"
        query SnapshotIntervals {
          snapshotIntervals {
            id
            filesystem_name: filesystemName
            use_barrier: useBarrier
            interval
            last_run: lastRun
          }
        }
    "#;

    pub fn build() -> Query<()> {
        Query {
            query: QUERY.to_string(),
            variables: None,
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "snapshotIntervals"))]
        pub snapshot_intervals: Vec<SnapshotInterval>,
    }
}

/// Graphql query to create a new retention. Note that
/// Snapshots will automatically be deleted (starting with the oldest)
/// when free space falls below the defined reserve value and its associated unit.
pub mod create_retention {
    use crate::Query;
    use emf_wire_types::snapshot::ReserveUnit;

    pub static QUERY: &str = r#"
        mutation CreateSnapshotRetention($fsname: String!, $reserve_value: Int!, $reserve_unit: ReserveUnit!, $keep_num: Int) {
            createSnapshotRetention(fsname: $fsname, reserveValue: $reserve_value, reserveUnit: $reserve_unit, keepNum: $keep_num)
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        fsname: String,
        reserve_value: u32,
        reserve_unit: ReserveUnit,
        keep_num: Option<u32>,
    }

    pub fn build(
        fsname: impl ToString,
        reserve_value: u32,
        reserve_unit: ReserveUnit,
        keep_num: Option<u32>,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                fsname: fsname.to_string(),
                reserve_value,
                reserve_unit,
                keep_num,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "createSnapshotRetention"))]
        pub create_snapshot_retention: bool,
    }
}

pub mod remove_retention {
    use crate::Query;

    pub static QUERY: &str = r#"
        mutation RemoveSnapshotRetention($id: Int!) {
          removeSnapshotRetention(id: $id)
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        id: i32,
    }

    pub fn build(id: i32) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars { id }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "removeSnapshotRetention"))]
        pub remove_snapshot_retention: bool,
    }
}

/// Graphql query to list retentions. For each retention, snapshots will automatically
/// be deleted (starting with the oldest) when free space falls below the defined reserve
/// value and its associated unit.
pub mod list_retentions {
    use crate::Query;
    use emf_wire_types::snapshot::SnapshotRetention;

    pub static QUERY: &str = r#"
        query SnapshotRetentionPolicies {
          snapshotRetentionPolicies {
            id
            filesystem_name: filesystemName
            reserve_value: reserveValue
            reserve_unit: reserveUnit
            keep_num: keepNum
            last_run: lastRun
          }
        }
    "#;

    pub fn build() -> Query<()> {
        Query {
            query: QUERY.to_string(),
            variables: None,
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "snapshotRetentionPolicies"))]
        pub snapshot_retention_policies: Vec<SnapshotRetention>,
    }
}
