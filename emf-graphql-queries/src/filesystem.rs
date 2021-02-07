// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Resp<T> {
    pub filesystem: T,
}

pub mod list {
    use crate::Query;
    use emf_wire_types::Filesystem;

    pub static QUERY: &str = r#"
        query ListFilesystems {
          filesystem {
            list {
              id
              state_modified_at: stateModifiedAt
              state
              name
              mdt_next_index: mdtNextIndex
              ost_next_index: ostNextIndex
              mgs_id: mgsId
              mdt_ids: mdtIds
              ost_ids: ostIds
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
    pub struct FilesystemList {
        pub list: Vec<Filesystem>,
    }

    pub type Resp = super::Resp<FilesystemList>;
}

pub mod by_name {
    use crate::Query;
    use emf_wire_types::Filesystem;

    pub static QUERY: &str = r#"
        query FsByName($name: String!) {
            filesystem {
                by_name(name: $name) {
                    id
                    state_modified_at
                    state
                    name
                    mdt_next_index
                    ost_next_index
                    mgs_id
                    mdt_ids
                    ost_ids
                }
            }
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        name: String,
    }

    pub fn build(name: impl ToString) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                name: name.to_string(),
            }),
        }
    }

    #[derive(Debug, Clone, serde::Deserialize)]
    pub struct FilesystemByName {
        #[serde(rename(deserialize = "byName"))]
        pub by_name: Option<Filesystem>,
    }

    pub type Resp = super::Resp<FilesystemByName>;
}
