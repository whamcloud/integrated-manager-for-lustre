// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use structopt::StructOpt;

#[derive(StructOpt, Debug)]
pub struct SshOpts {
    /// SSH port
    #[structopt(long, default_value = "22")]
    pub port: u16,
    /// SSH user
    #[structopt(long, default_value = "root")]
    pub user: String,
    #[structopt(flatten)]
    pub auth_opts: AuthOpts,
}

#[derive(StructOpt, Debug)]
pub struct AuthOpts {
    /// Use ssh-agent to authenticate
    #[structopt(long, conflicts_with_all = &["key_path", "key_passphrase", "password"])]
    pub agent: bool,
    /// Use password authentication
    #[structopt(long, conflicts_with_all = &["key_path", "key_passphrase"])]
    pub password: Option<String>,
    /// Use private key authentication
    #[structopt(long)]
    pub key_path: Option<String>,
    /// Private key passphrase
    #[structopt(long, requires = "key_path")]
    pub key_passphrase: Option<String>,
}

impl From<&AuthOpts> for emf_ssh::Auth {
    fn from(opts: &AuthOpts) -> Self {
        if opts.agent {
            Self::Agent
        } else if let Some(pw) = &opts.password {
            Self::Password(pw.to_string())
        } else if let Some(key_path) = &opts.key_path {
            Self::Key {
                key_path: key_path.to_string(),
                password: opts.key_passphrase.as_ref().map(|x| x.to_string()),
            }
        } else {
            Self::Auto
        }
    }
}
