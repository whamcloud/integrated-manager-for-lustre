// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, daemon_plugins::postoffice, env};
use futures::future::TryFutureExt;
use std::{collections::HashMap, fmt, path::PathBuf};
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
    /// Lustre device to be mounted, e.g. `192.168.0.100@tcp0:/spfs`
    mountpoint: String,

    #[structopt(long)]
    /// IML mailbox name, e.g. `mailbox1`, where `lamigo` will write FIDs
    mailbox: String,
}

impl Config {
    fn generate_unit(&self, mailbox: String) -> String {
        format!(
            "mdt={fs}-MDT{mdt:04x}\n\
             mountpoint={mountpoint}\n\
             user={user}\n\
             min-age={age}\n\
             src={fast}\n\
             tgt={slow}\n\
             iml-socket={mailbox}\n\
             ",
            fs = self.fs,
            mdt = self.mdt,
            mountpoint = self.mountpoint,
            user = self.user,
            age = self.min_age,
            fast = self.hot_pool,
            slow = self.cold_pool,
            mailbox = mailbox,
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
    vars.insert("mailbox".to_string(), &c.mailbox);
    strfmt::strfmt(&path_fmt, &vars)
}

fn format_lamigo_conf_file(c: &Config, path_fmt: &str) -> Result<PathBuf, ImlAgentError> {
    Ok(PathBuf::from(expand_path_fmt(path_fmt, &c)?))
}

fn format_lamigo_unit_file(c: &Config) -> PathBuf {
    PathBuf::from(format!(
        "/etc/systemd/system/lamigo-{}-MDT{:04x}.service",
        c.fs, c.mdt
    ))
}

fn format_lamigo_unit_contents(c: &Config, path_fmt: &str) -> Result<String, ImlAgentError> {
    Ok(format!(
        "[Unit]\n\
         Description=Run lamigo service for {fs}-MDT{mdt:04x}\n\
         \n\
         [Service]\n\
         ExecStartPre=/usr/bin/lfs df {mountpoint}\n\
         ExecStart=/usr/bin/lamigo -f {conf}\n",
        mountpoint = c.mountpoint,
        conf = format_lamigo_conf_file(c, path_fmt)?.to_string_lossy(),
        fs = c.fs,
        mdt = c.mdt,
    ))
}

async fn write(file: PathBuf, cnt: String) -> Result<(), ImlAgentError> {
    if let Some(parent) = file.parent() {
        fs::create_dir_all(&parent).await?;
    }
    fs::write(file, cnt.as_bytes()).err_into().await
}

pub async fn create_lamigo_service_unit(c: Config) -> Result<(), ImlAgentError> {
    let path_fmt = env::get_var("LAMIGO_CONF_PATH");

    let path = format_lamigo_conf_file(&c, &path_fmt)?;
    let cnt = c.generate_unit(env::mailbox_sock(&c.mailbox));
    write(path, cnt).await?;

    let path = format_lamigo_unit_file(&c);
    let cnt = format_lamigo_unit_contents(&c, &path_fmt)?;
    write(path, cnt).await
}

#[cfg(test)]
mod lamigo_tests {
    use super::*;
    use insta::assert_display_snapshot;
    use std::env;

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
            mailbox: "mailbox".into(),
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
            mailbox: "mailbox".into(),
        };

        assert_eq!(
            format_lamigo_conf_file(&config, "/etc/lamigo/{fs}-{mdt}.conf").unwrap(),
            PathBuf::from("/etc/lamigo/LU_TEST1-MDT0010.conf")
        )
    }

    #[tokio::test]
    async fn test_works() {
        let config = Config {
            fs: "LU_TEST2".into(),
            mdt: 17,
            user: "nick".into(),
            min_age: 35353,
            mailbox: "mailbox2".into(),
            mountpoint: "/mnt/spfs".into(),
            hot_pool: "FAST_POOL".into(),
            cold_pool: "SLOW_POOL".into(),
        };

        let content = format_lamigo_unit_contents(&config, "/etc/lamigo/{fs}-{mdt}.conf")
            .expect("cannot generate unit");

        assert_display_snapshot!(content);
    }
}
