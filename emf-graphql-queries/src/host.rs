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

pub mod deploy {
    use crate::Query;
    use emf_wire_types::{
        ssh::{AuthOpts, ProxyInput},
        CommandOrDryRun, Flavor,
    };

    pub static QUERY: &str = r#"
        mutation DeployHost($hosts: [String!]!, $flavor: Flavor!, $dry_run: Boolean!, $ssh_port: Int, $ssh_user: String, $auth_opts: AuthOpts, $proxy_opts: ProxyInput) {
          host {
            deploy(hosts: $hosts, flavor: $flavor, dryRun: $dry_run, sshPort: $ssh_port, sshUser: $ssh_user, authOpts: $auth_opts, proxyOpts: $proxy_opts) {
              ... on Command {
                id
                plan
                state
              }
              ... on DryRun {
                yaml
              }
            }
          }
        }
    "#;

    #[derive(Debug, serde::Serialize)]
    pub struct Vars {
        hosts: Vec<String>,
        flavor: Flavor,
        dry_run: bool,
        ssh_port: Option<u16>,
        ssh_user: Option<String>,
        auth_opts: Option<AuthOpts>,
        proxy_opts: Option<ProxyInput>,
    }

    pub fn build(
        hosts: Vec<String>,
        flavor: Flavor,
        dry_run: bool,
        ssh_port: impl Into<Option<u16>>,
        ssh_user: impl Into<Option<String>>,
        auth_opts: impl Into<Option<AuthOpts>>,
        proxy_opts: impl Into<Option<ProxyInput>>,
    ) -> Query<Vars> {
        Query {
            query: QUERY.to_string(),
            variables: Some(Vars {
                hosts,
                flavor,
                dry_run,
                ssh_port: ssh_port.into(),
                ssh_user: ssh_user.into(),
                auth_opts: auth_opts.into(),
                proxy_opts: proxy_opts.into(),
            }),
        }
    }

    #[derive(Debug, serde::Deserialize)]
    pub struct Deploy {
        pub deploy: CommandOrDryRun,
    }

    pub type Resp = super::Resp<Deploy>;
}
