// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Resp<T> {
    pub snapshot: T,
}

pub mod create {
    use crate::Query;
    use iml_wire_types::Command;

    pub static QUERY: &str = r#"
        mutation CreateSnapshot($fsname: String!, $name: String!, $comment: String, $use_barrier: Boolean) {
            snapshot {
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
    pub struct CreateSnapshot {
        #[serde(rename(deserialize = "createSnapshot"))]
        pub create: Command,
    }

    pub type Resp = super::Resp<CreateSnapshot>;
}

pub mod destroy {
    use crate::Query;
    use iml_wire_types::Command;

    pub static QUERY: &str = r#"
        mutation DestroySnapshot($fsname: String!, $name: String!, $force: Boolean!) {
            snapshot {
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
    pub struct DestroySnapshot {
        #[serde(rename(deserialize = "destroySnapshot"))]
        pub destroy: Command,
    }

    pub type Resp = super::Resp<DestroySnapshot>;
}

pub mod mount {
    use crate::Query;
    use iml_wire_types::Command;

    pub static QUERY: &str = r#"
        mutation MountSnapshot($fsname: String!, $name: String!) {
            snapshot {
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
    pub struct MountSnapshot {
        #[serde(rename(deserialize = "mountSnapshot"))]
        pub mount: Command,
    }

    pub type Resp = super::Resp<MountSnapshot>;
}

pub mod unmount {
    use crate::Query;
    use iml_wire_types::Command;

    pub static QUERY: &str = r#"
        mutation UnmountSnapshot($fsname: String!, $name: String!) {
            snapshot {
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
    pub struct UnmountSnapshot {
        #[serde(rename(deserialize = "unmountSnapshot"))]
        pub unmount: Command,
    }

    pub type Resp = super::Resp<UnmountSnapshot>;
}

pub mod list {
    use crate::Query;
    use iml_wire_types::{snapshot::Snapshot, SortDir};

    pub static QUERY: &str = r#"
        query Snapshots($fsname: String!, $name: String, $dir: SortDir, $offset: Int, $limit: Int) {
            snapshot {
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
    pub struct ListSnapshots {
        #[serde(rename(deserialize = "snapshots"))]
        pub snapshots: Vec<Snapshot>,
    }

    pub type Resp = super::Resp<ListSnapshots>;
}

pub mod policy {
    pub mod list {
        use crate::Query;
        use iml_wire_types::snapshot::SnapshotPolicy;

        pub static QUERY: &str = r#"
            query SnapshotPolicies {
                snapshot {
                      snapshotPolicies {
                        id
                        filesystem
                        interval
                        start
                        barrier
                        keep
                        daily
                        weekly
                        monthly
                        last_run: lastRun
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

        #[derive(Debug, Clone, serde::Deserialize)]
        pub struct ListPolicies {
            #[serde(rename(deserialize = "snapshotPolicies"))]
            pub policies: Vec<SnapshotPolicy>,
        }

        pub type Resp = super::super::Resp<ListPolicies>;
    }

    pub mod create {
        use crate::Query;

        pub static QUERY: &str = r#"
            mutation CreateSnapshotPolicy($filesystem: String!, $interval: Duration!, $barrier: Boolean, $start: DateTimeUtc,
                                          $keep: Int!, $daily: Int, $weekly: Int, $monthly: Int) {
                snapshot {
                    createSnapshotPolicy(filesystem: $filesystem, interval: $interval, barrier: $barrier, start: $start,
                                            keep: $keep, daily: $daily, weekly: $weekly, monthly: $monthly)
                }
            }
        "#;

        #[derive(Debug, serde::Serialize, Default, Clone)]
        pub struct Vars {
            pub filesystem: String,
            pub interval: String,
            pub start: Option<String>,
            pub barrier: Option<bool>,
            pub keep: i32,
            pub daily: Option<i32>,
            pub weekly: Option<i32>,
            pub monthly: Option<i32>,
        }

        pub fn build(vars: Vars) -> Query<Vars> {
            Query {
                query: QUERY.to_string(),
                variables: Some(vars),
            }
        }

        #[derive(Debug, Clone, serde::Deserialize)]
        pub struct CreateSnapshotPolicy {
            #[serde(rename(deserialize = "createSnapshotPolicy"))]
            pub created: bool,
        }

        pub type Resp = super::super::Resp<CreateSnapshotPolicy>;
    }

    pub mod remove {
        use crate::Query;

        pub static QUERY: &str = r#"
            mutation RemoveSnapshotPolicy($filesystem: String!) {
                  snapshot {
                      removeSnapshotPolicy(filesystem: $filesystem)
                  }
            }
        "#;

        #[derive(Debug, serde::Serialize, Default)]
        pub struct Vars {
            filesystem: String,
        }

        pub fn build(filesystem: impl ToString) -> Query<Vars> {
            Query {
                query: QUERY.to_string(),
                variables: Some(Vars {
                    filesystem: filesystem.to_string(),
                }),
            }
        }

        #[derive(Debug, Clone, serde::Deserialize)]
        pub struct RemoveSnapshotPolicy {
            #[serde(rename(deserialize = "removeSnapshotPolicy"))]
            pub removed: bool,
        }

        pub type Resp = super::super::Resp<RemoveSnapshotPolicy>;
    }
}
