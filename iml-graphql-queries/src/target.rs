// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod list {
    use crate::Query;
    use iml_wire_types::{db::TargetRecord, SortDir};

    pub static QUERY: &str = r#"
            query Targets($limit: Int, $offset: Int, $dir: SortDir, $fsname: String, $exclude_unmounted: Boolean) {
              targets(limit: $limit, offset: $offset, dir: $dir, fsName: $fsname, excludeUnmounted: $exclude_unmounted) {
                id
                state
                name
                dev_path: devPath
                active_host_id: activeHostId
                host_ids: hostIds
                filesystems
                uuid
                mount_path: mountPath
                fs_type: fsType
              }
            }
        "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        limit: Option<u32>,
        offset: Option<u32>,
        dir: Option<SortDir>,
        fsname: Option<String>,
        exclude_unmounted: Option<bool>,
    }

    pub fn build(
        limit: Option<u32>,
        offset: Option<u32>,
        dir: Option<SortDir>,
        fsname: Option<String>,
        exclude_unmounted: Option<bool>,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                limit,
                offset,
                dir,
                fsname,
                exclude_unmounted,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        pub targets: Vec<TargetRecord>,
    }
}
