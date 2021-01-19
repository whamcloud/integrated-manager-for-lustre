// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Resp<T> {
    pub filesystem: T,
}

pub mod detect {
    use crate::Query;

    pub static QUERY: &str = r#"
        mutation {
          filesystem {
            detect
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
    pub struct Detect {
        pub detect: bool,
    }

    pub type Resp = super::Resp<Detect>;
}
