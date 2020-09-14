// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod create {
    use crate::Query;
    use iml_wire_types::Command;

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
    use iml_wire_types::Command;

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
    use iml_wire_types::Command;

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
    use iml_wire_types::Command;

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
    use crate::{Query, SortDir};
    use iml_wire_types::snapshot::Snapshot;

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
