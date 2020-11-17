// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod list {
    use crate::Query;

    pub static QUERY: &str = r#"
        query clientMountCommand($fsName: String!) {
            clientMountCommand(fsName:$fsName)
        }
        "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        #[serde(rename = "fsName")]
        fs_name: String,
    }

    pub fn build(fs_name: String) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars { fs_name }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "clientMountCommand"))]
        pub client_mount_command: String,
    }
}
