// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod server_profiles {
    use crate::Query;
    use iml_wire_types::graphql;

    pub static QUERY: &str = r#"
            query ServerProfiles {
                serverProfiles {
                    corosync
                    corosync2
                    default
                    initialState
                    managed
                    name
                    ntp
                    pacemaker
                    repos {
                        name
                        location
                    }
                    uiDescription
                    uiName
                    userSelectable
                    worker
                }
            }
        "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {}

    pub fn build() -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {}),
        }
    }

    #[derive(serde::Deserialize, Clone, Debug)]
    pub struct Resp {
        #[serde(rename(deserialize = "serverProfiles"))]
        pub server_profiles: Vec<graphql::ServerProfile>,
    }
}
