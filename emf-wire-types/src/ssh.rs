// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug, serde::Serialize)]
#[cfg_attr(feature = "cli", derive(structopt::StructOpt))]
pub struct SshOpts {
    /// SSH port
    #[cfg_attr(feature = "cli", structopt(long, default_value = "22"))]
    pub port: u16,
    /// SSH user
    #[cfg_attr(feature = "cli", structopt(long, default_value = "root"))]
    pub user: String,
    #[cfg_attr(feature = "cli", structopt(flatten))]
    pub auth_opts: AuthOpts,
    #[cfg_attr(feature = "cli", structopt(flatten))]
    pub proxy_opts: ProxyOpts,
}

/// Proxy through this host to reach the destination
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLInputObject))]
#[derive(Debug, serde::Serialize)]
pub struct ProxyInput {
    /// SSH Proxy host
    pub host: String,
    /// SSH Proxy port
    pub port: Option<i32>,
    /// SSH Proxy user
    pub user: Option<String>,
    /// SSH Proxy password
    pub password: Option<String>,
}

impl From<ProxyOpts> for Option<ProxyInput> {
    fn from(
        ProxyOpts {
            host,
            port,
            user,
            password,
        }: ProxyOpts,
    ) -> Self {
        let host = host?;

        Some(ProxyInput {
            host,
            port: port.map(|x| x as i32),
            user,
            password,
        })
    }
}

#[derive(Debug, serde::Serialize)]
#[cfg_attr(feature = "cli", derive(structopt::StructOpt))]
pub struct ProxyOpts {
    /// SSH proxy host. This option must be set to use other proxy options
    #[cfg_attr(feature = "cli", structopt(name = "proxy_host", long = "proxy_host"))]
    pub host: Option<String>,
    /// SSH proxy port
    #[cfg_attr(
        feature = "cli",
        structopt(long = "proxy_port", name = "proxy_port", requires = "proxy_host")
    )]
    pub port: Option<u16>,

    /// SSH proxy user
    #[cfg_attr(
        feature = "cli",
        structopt(long = "proxy_user", name = "proxy_user", requires = "proxy_host")
    )]
    pub user: Option<String>,
    /// SSH proxy password. If not set, key auth will be used
    #[cfg_attr(
        feature = "cli",
        structopt(
            long = "proxy_password",
            env = "PROXY_PASSWORD",
            hide_env_values = true,
            name = "proxy_password",
            requires = "proxy_host"
        )
    )]
    pub password: Option<String>,
}

#[derive(Debug, serde::Serialize)]
#[cfg_attr(feature = "cli", derive(structopt::StructOpt))]
#[cfg_attr(feature = "graphql", derive(juniper::GraphQLInputObject))]
#[serde(rename_all = "camelCase")]
pub struct AuthOpts {
    /// Use ssh-agent to authenticate
    #[cfg_attr(feature = "cli", structopt(long, group = "auth"))]
    pub agent: bool,
    /// Use password authentication
    #[cfg_attr(
        feature = "cli",
        structopt(long, env = "SSH_PASSWORD", hide_env_values = true, group = "auth")
    )]
    pub password: Option<String>,
    /// Use private key authentication
    #[cfg_attr(feature = "cli", structopt(long, group = "auth"))]
    pub key_path: Option<String>,
    /// Private key passphrase
    #[cfg_attr(
        feature = "cli",
        structopt(
            long,
            env = "SSH_KEY_PASSPHRASE",
            hide_env_values = true,
            requires = "key_path"
        )
    )]
    pub key_passphrase: Option<String>,
}
