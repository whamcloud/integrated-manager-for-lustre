// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod query {
    use crate::Query;

    #[derive(serde::Serialize)]
    pub enum SortDir {
        Asc,
        Desc,
    }

    pub static QUERY: &str = r#"
        query Targets($limit: Int, $offset: Int, $dir: SortDir, $fs_name: String, $exclude_unmounted: Boolean!) {
            targets(limit: $limit, offset: $offset, dir: $dir, fsName: $fs_name, excludeUnmounted: $exclude_unmounted) {
            name
            state
            activeHostId
            hostIds
            filesystems
            uuid
            mountPath
            }
        }
        "#;

    #[derive(serde::Serialize)]
    pub struct Vars {
        exclude_unmounted: bool,
        fs_name: Option<String>,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
    }

    pub fn build(
        exclude_unmounted: bool,
        fs_name: Option<impl ToString>,
        limit: Option<i32>,
        offset: Option<i32>,
        dir: Option<SortDir>,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                exclude_unmounted,
                fs_name: fs_name.map(|x| x.to_string()),
                limit,
                offset,
                dir,
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        pub targets: Vec<iml_device::Target>,
    }
}
