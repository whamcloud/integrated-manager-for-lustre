// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod list {
    use crate::Query;
    use emf_wire_types::graphql;

    pub static QUERY: &str = r#"
          query serverProfiles {
            server_profiles: serverProfiles {
              corosync
              corosync2
              default
              initial_state: initialState
              managed
              name
              ntp
              pacemaker
              repos {
                name
                location
              }
              ui_description: uiDescription
              ui_name: uiName
              user_selectable: userSelectable
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
        pub server_profiles: Vec<graphql::ServerProfile>,
    }
}

pub mod create {
    use crate::Query;
    use emf_wire_types::graphql::ServerProfileInput;

    pub static QUERY: &str = r#"
          mutation CreateServerProfile($profile: ServerProfileInput!) {
            createServerProfile(profile: $profile)
          }
        "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        profile: ServerProfileInput,
    }

    pub fn build(profile: ServerProfileInput) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars { profile }),
        }
    }

    #[derive(serde::Deserialize, Clone, Debug)]
    pub struct Resp {
        #[serde(rename(deserialize = "createServerProfile"))]
        pub create_server_profile: bool,
    }
}

pub mod remove {
    use crate::Query;

    pub static QUERY: &str = r#"
          mutation RemoveServerProfile($profileName: String!) {
            removeServerProfile(profileName: $profileName)
          }  
        "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        #[serde(rename(serialize = "profileName"))]
        profile_name: String,
    }

    pub fn build(profile_name: &str) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                profile_name: profile_name.into(),
            }),
        }
    }

    #[derive(serde::Deserialize, Clone, Debug)]
    pub struct Resp {
        #[serde(rename(deserialize = "removeServerProfile"))]
        pub remove_server_profile: bool,
    }
}
