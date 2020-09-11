// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod create {
    use crate::Query;

    pub const QUERY: &str = r#"
            mutation CreateSnapshot($fsname: String!, $name: String!, $comment: String, $use_barrier: Boolean) {
              createSnapshot(fsname: $fsname, name: $name, comment: $comment, use_barrier: $use_barrier) {
                cancelled
                complete
                createdAt
                errored
                id
                jobs
                logs
                message
                resourceUri
              }
            }
        "#;

    #[derive(serde::Serialize)]
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
}
