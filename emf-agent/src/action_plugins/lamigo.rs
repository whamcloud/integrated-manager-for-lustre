// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::EmfAgentError, env};
use futures::future::TryFutureExt;
use std::{collections::HashMap, path::PathBuf};
use tokio::fs;

#[derive(serde::Deserialize, structopt::StructOpt, Clone, Debug)]
pub struct Config {
    #[structopt(long)]
    /// File system name
    fs: String,

    #[structopt(long)]
    /// MDT device index that provides changelogs
    mdt: u32,

    #[structopt(long)]
    /// The changelog user (e.g. cl1)
    user: String,

    #[structopt(long)]
    /// Fast OST pool name
    hot_pool: String,

    #[structopt(long)]
    /// Slow OST pool name
    cold_pool: String,

    #[structopt(long)]
    /// Interval for lamigo to wait before replicating a closed file (in seconds)
    min_age: u32,

    #[structopt(long)]
    /// Local mountpoint of lustre client
    mountpoint: String,

    #[structopt(long)]
    /// EMF mailbox name, e.g. `mailbox1`, where `lamigo` will write FIDs for mirror extend
    mailbox_extend: String,

    #[structopt(long)]
    /// EMF mailbox name, e.g. `mailbox2`, where `lamigo` will write FIDs for mirror resync
    mailbox_resync: String,

    #[structopt(long)]
    heatfn: Option<u32>,
}

impl Config {
    fn generate_unit(&self, mailbox_extend: String, mailbox_resync: String) -> String {
        format!(
            "mdt={fs}-MDT{mdt:04x}\n\
             mount={mountpoint}\n\
             user={user}\n\
             min-age={age}\n\
             src={fast}\n\
             tgt={slow}\n\
             emf-ex-socket={extend}\n\
             emf-re-socket={resync}\n\
             heatfn={heatfn}\n\
             ",
            fs = self.fs,
            mdt = self.mdt,
            mountpoint = self.mountpoint,
            user = self.user,
            age = self.min_age,
            fast = self.hot_pool,
            slow = self.cold_pool,
            extend = mailbox_extend,
            resync = mailbox_resync,
            heatfn = if let Some(val) = self.heatfn {
                format!("{}", val)
            } else {
                "none".into()
            },
        )
    }
}

fn expand_path_fmt(path_fmt: &str, c: &Config) -> strfmt::Result<String> {
    let mut vars = HashMap::new();
    let min_age_str = c.min_age.to_string();
    let mdt = format!("MDT{:04x}", c.mdt);
    vars.insert("fs".to_string(), &c.fs);
    vars.insert("mdt".to_string(), &mdt);
    vars.insert("user".to_string(), &c.user);
    vars.insert("hot_pool".to_string(), &c.hot_pool);
    vars.insert("cold_pool".to_string(), &c.cold_pool);
    vars.insert("min_age".to_string(), &min_age_str);
    strfmt::strfmt(&path_fmt, &vars)
}

fn format_lamigo_conf_file(c: &Config, path_fmt: &str) -> Result<PathBuf, EmfAgentError> {
    Ok(PathBuf::from(expand_path_fmt(path_fmt, &c)?))
}

async fn write(file: PathBuf, cnt: String) -> Result<(), EmfAgentError> {
    if let Some(parent) = file.parent() {
        fs::create_dir_all(&parent).await?;
    }
    fs::write(file, cnt.as_bytes()).err_into().await
}

pub async fn create_lamigo_conf(c: Config) -> Result<(), EmfAgentError> {
    let path_fmt = env::get_var("LAMIGO_CONF_PATH");

    let path = format_lamigo_conf_file(&c, &path_fmt)?;
    let cnt = c.generate_unit(
        env::mailbox_sock(&c.mailbox_extend),
        env::mailbox_sock(&c.mailbox_resync),
    );
    write(path, cnt).await
}

#[cfg(test)]
mod lamigo_tests {
    use super::*;

    #[test]
    fn test_expand_path_fmt() {
        let config = Config {
            fs: "LU_TEST1".into(),
            mdt: 16,
            user: "nick".into(),
            hot_pool: "FAST_POOL".into(),
            cold_pool: "SLOW_POOL".into(),
            min_age: 35353,
            mountpoint: "/mnt/spfs".into(),
            mailbox_extend: "mailbox-extend".into(),
            mailbox_resync: "mailbox-resync".into(),
            heatfn: None,
        };
        let fmt1 = "/etc/systemd/system/lamigo-{fs}-{mdt}.service";
        assert_eq!(
            expand_path_fmt(fmt1, &config),
            Ok("/etc/systemd/system/lamigo-LU_TEST1-MDT0010.service".to_string())
        );

        let fmt2 = "/tmp/{user}/lamigo-{fs}-{hot_pool}.test";
        assert_eq!(
            expand_path_fmt(fmt2, &config),
            Ok("/tmp/nick/lamigo-LU_TEST1-FAST_POOL.test".to_string())
        );

        let fmt3 = "lamigo-{unknown_value}.service";
        assert!(expand_path_fmt(fmt3, &config).is_err());
    }

    #[test]
    fn test_expand_path_fmt_env() {
        let config = Config {
            fs: "LU_TEST1".into(),
            mdt: 16,
            user: "nick".into(),
            hot_pool: "FAST_POOL".into(),
            cold_pool: "SLOW_POOL".into(),
            min_age: 35353,
            mountpoint: "/mnt/spfs".into(),
            mailbox_extend: "mailbox-extend".into(),
            mailbox_resync: "mailbox-resync".into(),
            heatfn: None,
        };

        assert_eq!(
            format_lamigo_conf_file(&config, "/etc/lamigo/{fs}-{mdt}.conf").unwrap(),
            PathBuf::from("/etc/lamigo/LU_TEST1-MDT0010.conf")
        )
    }
}
