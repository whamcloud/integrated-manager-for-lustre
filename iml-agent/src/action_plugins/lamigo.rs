// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env};
use futures::future::TryFutureExt;
use std::collections::HashMap;
use std::fmt;
use std::path::Path;
use tokio::fs;
use tokio::io::AsyncWriteExt;

#[derive(serde::Deserialize, structopt::StructOpt, Clone, Debug)]
pub struct Config {
    #[structopt(long)]
    /// File system name
    fs: String,

    #[structopt(long)]
    /// MDT device that provides changelogs
    mdt: String,

    #[structopt(long)]
    /// The user on which behalf lamigo consumes changelogs from the MDT device
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
    /// Lustre client mount point, e.g. `/mnt/lustre`
    mount_point: String,

    #[structopt(long)]
    /// Lustre device to be mounted, e.g. `192.168.0.100@tcp0:/spfs`
    lustre_device: String,
}

impl fmt::Display for Config {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "[Unit]\n\
             Description=Run lamigo service\n\
             [Service]\n\
             ExecStart=/usr/bin/lamigo \
             -m {fs}-{mdt} \
             -u {user} \
             -s {hot_pool} \
             -t {cold_pool} \
             -a {min_age} \
             {mount_point}\n\
             ",
            fs = self.fs,
            mdt = self.mdt,
            cold_pool = self.cold_pool,
            hot_pool = self.hot_pool,
            min_age = self.min_age,
            user = self.user,
            mount_point = self.mount_point,
        )
    }
}

pub async fn create_lamigo_service_unit(c: Config) -> Result<(), ImlAgentError> {
    let path_fmt = env::get_var("LAMIGO_UNIT_PATH");
    let path = expand_path_fmt(&path_fmt, &c)?;
    create_lamigo_service_unit_internal(path, &c)
        .err_into()
        .await
}

fn expand_path_fmt(path_fmt: &str, c: &Config) -> strfmt::Result<String> {
    let mut vars = HashMap::new();
    let min_age_str = c.min_age.to_string();
    vars.insert("fs".to_string(), &c.fs);
    vars.insert("mdt".to_string(), &c.mdt);
    vars.insert("user".to_string(), &c.user);
    vars.insert("hot_pool".to_string(), &c.hot_pool);
    vars.insert("cold_pool".to_string(), &c.cold_pool);
    vars.insert("min_age".to_string(), &min_age_str);
    vars.insert("mount_point".to_string(), &c.mount_point);
    vars.insert("lustre_device".to_string(), &c.lustre_device);
    // path_fmt is like "/etc/systemd/system/lamigo-{fs}-{mdt}.service"
    strfmt::strfmt(&path_fmt, &vars)
}

async fn create_lamigo_service_unit_internal<P: AsRef<Path>>(
    file_path: P,
    c: &Config,
) -> std::io::Result<()> {
    if let Some(dir_path) = file_path.as_ref().parent() {
        fs::create_dir_all(&dir_path).await?;
    };
    let mut file = fs::File::create(file_path).await?;
    let cnt = format!("{}", c);
    file.write_all(cnt.as_bytes()).await?;
    Ok(())
    // fs::write(file, cnt.as_bytes()).await
}

#[cfg(test)]
mod lamigo_tests {
    use super::*;
    use insta::assert_display_snapshot;
    use tempfile::tempdir;

    #[test]
    fn test_expand_path_fmt() {
        let config = Config {
            fs: "LU_TEST1".into(),
            mdt: "MDT000".into(),
            user: "nick".into(),
            min_age: 35353,
            mount_point: "/mnt/lustre".into(),
            lustre_device: "192.168.0.100@tcp0:/spfs".into(),
            hot_pool: "FAST_POOL".into(),
            cold_pool: "SLOW_POOL".into(),
        };
        let fmt1 = "/etc/systemd/system/lamigo-{fs}-{mdt}.service";
        assert_eq!(
            expand_path_fmt(fmt1, &config),
            Ok("/etc/systemd/system/lamigo-LU_TEST1-MDT000.service".to_string())
        );

        let fmt2 = "/tmp/{user}/lamigo-{fs}-{mdt}.service";
        assert_eq!(
            expand_path_fmt(fmt2, &config),
            Ok("/tmp/nick/lamigo-LU_TEST1-MDT000.service".to_string())
        );

        let fmt3 = "lamigo-{unknown_value}.service";
        assert_eq!(
            expand_path_fmt(fmt3, &config),
            Err(strfmt::FmtError::KeyError(
                "Invalid key: unknown_value".to_string()
            ))
        );
    }

    #[tokio::test]
    async fn test_works() {
        // cargo run --package iml-agent --bin iml-agent -- lamigo
        // --cold_pool SLOW_POOL --hot_pool FAST_POOL
        // --fs LU_TEST2 --lustre_device 192.168.0.100@tcp0:/spfs
        // --mdt MDT000 --min_age 35353 --user nick --mount_point /mnt/lustre
        let config = Config {
            fs: "LU_TEST2".into(),
            mdt: "MDT000".into(),
            user: "nick".into(),
            min_age: 35353,
            mount_point: "/mnt/lustre".into(),
            lustre_device: "192.168.0.100@tcp0:/spfs".into(),
            hot_pool: "FAST_POOL".into(),
            cold_pool: "SLOW_POOL".into(),
        };

        let dir = tempdir().expect("could not create tmpdir");
        let expected_file = dir.path().join("lamigo-LU_TEST2-MDT000.service");
        create_lamigo_service_unit_internal(&expected_file, &config)
            .await
            .expect("could not write ");

        let bytes = fs::read(expected_file).await.unwrap();
        let content = String::from_utf8_lossy(&bytes);
        assert_display_snapshot!(content);
    }
}
