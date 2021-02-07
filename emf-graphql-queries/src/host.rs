// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, Clone, serde::Deserialize)]
pub struct Resp<T> {
    pub host: T,
}

pub mod list {
    use crate::Query;
    use emf_wire_types::Host;

    pub static QUERY: &str = r#"
        query ListHosts {
          host {
            list {
              id
              state
              fqdn
              machine_id: machineId
              boot_time: bootTime
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
    pub struct HostList {
        pub list: Vec<Host>,
    }

    pub type Resp = super::Resp<HostList>;
}
