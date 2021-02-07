// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Resp<T> {
    pub ost_pool: T,
}

pub mod list {
    use crate::Query;
    use emf_wire_types::OstPoolGraphql;

    pub static QUERY: &str = r#"
        query ListOstPools($fsname: String, $poolname: String) {
          ostPool {
            list(fsname: $fsname, poolname: $poolname) {
              id
              name
              filesystem
              osts
            }
          }
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        fsname: Option<String>,
        poolname: Option<String>,
    }

    pub fn build(fsname: Option<String>, poolname: Option<String>) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars { fsname, poolname }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct OstPoolList {
        pub list: Vec<OstPoolGraphql>,
    }

    pub type Resp = super::Resp<OstPoolList>;
}
