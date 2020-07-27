// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod ldev_create {
    use crate::Query;
    use iml_wire_types::Command;

    pub static QUERY: &str = r#"
        mutation CreateLdevConf {
            createLdevConf {
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

    pub fn build() -> Query<()> {
        Query {
            query: QUERY.to_string(),
            variables: None,
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct Resp {
        #[serde(rename(deserialize = "createLdevConf"))]
        pub create_ldev_conf: Command,
    }
}
