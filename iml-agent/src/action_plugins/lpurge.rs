// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, daemon_plugins::postoffice, env};
use futures::future::TryFutureExt;
use std::{collections::HashMap, fmt, path::PathBuf};
use tokio::fs;

#[derive(serde::Deserialize, structopt::StructOpt, Debug)]
pub struct Config {
    #[structopt(long)]
    /// Filesystem Name
    fs: String,
    #[structopt(long)]
    /// Ost Index
    ost: u32,
    #[structopt(long)]
    /// OST pool name
    pool: String,
    #[structopt(long)]
    freelo: u8,
    #[structopt(long)]
    freehi: u8,
    #[structopt(long)]
    mailbox: String,
}

impl fmt::Display for Config {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "\
             device={fs}-OST{ost:04x}\n\
             dryrun=true\n\
             freehi={freehi}\n\
             freelo={freelo}\n\
             listen_socket={socket}\n\
             max_jobs=0\n\
             pool={fs}.{pool}\n\
             ",
            freehi = self.freehi,
            freelo = self.freelo,
            socket = postoffice::socket_name(&self.mailbox),
            ost = self.ost,
            fs = self.fs,
            pool = self.pool,
        )
    }
}

fn expand_path_fmt(path_fmt: &str, c: &Config) -> strfmt::Result<String> {
    let mut vars = HashMap::new();
    let ost = format!("OST{:04x}", c.ost);
    let freehi = c.freehi.to_string();
    let freelo = c.freelo.to_string();

    vars.insert("fs".to_string(), &c.fs);
    vars.insert("ost".to_string(), &ost);
    vars.insert("pool".to_string(), &c.pool);
    vars.insert("freehi".to_string(), &freehi);
    vars.insert("freelo".to_string(), &freelo);
    vars.insert("mailbox".to_string(), &c.mailbox);
    strfmt::strfmt(&path_fmt, &vars)
}

pub async fn create_lpurge_conf(c: Config) -> Result<(), ImlAgentError> {
    let file = conf_name(&c).await?;
    write(file, &c).err_into().await
}

async fn conf_name(c: &Config) -> Result<PathBuf, ImlAgentError> {
    let path_fmt = env::get_var("LPURGE_CONF_PATH");
    let path = PathBuf::from(expand_path_fmt(&path_fmt, c)?);
    Ok(path)
}

async fn write(file: PathBuf, c: &Config) -> std::io::Result<()> {
    if let Some(parent) = file.parent() {
        fs::create_dir_all(&parent).await?;
    }
    let cnt = format!("{}", c);
    fs::write(file, cnt.as_bytes()).await
}

#[cfg(test)]
mod lpurge_conf_tests {
    use super::*;
    use insta::assert_display_snapshot;
    use tempfile::tempdir;
    use std::env;

    #[tokio::test]
    async fn works() {
        // for postoffice::socket_name()
        env::set_var("SOCK_DIR", "/run/iml");
        let cfg = Config {
            fs: "lima".to_string(),
            pool: "santiago".to_string(),
            ost: 16,
            freehi: 123,
            freelo: 60,
            mailbox: "foobar".to_string(),
        };

        let dir = tempdir().expect("could not create temp file");
        let file = dir.path().join("config");
        let file2 = file.clone();
        
        write(file, &cfg).await.expect("could not write");

        let cnt = String::from_utf8(
            std::fs::read(&file2).expect("could not read file"),
        )
        .unwrap();

        assert_display_snapshot!(cnt);
    }

    #[tokio::test]
    async fn config_name() {
        env::set_var("LPURGE_CONF_PATH", "/etc/lpurge/{fs}/{ost}-{pool}.conf");
        let cfg = Config {
            fs: "lima".to_string(),
            pool: "santiago".to_string(),
            ost: 16,
            freehi: 123,
            freelo: 60,
            mailbox: "foobar".to_string(),
        };
        let file = conf_name(&cfg).await.expect("name could not be created");

        assert_eq!(file, PathBuf::from("/etc/lpurge/lima/OST0010-santiago.conf"));
    }
}
