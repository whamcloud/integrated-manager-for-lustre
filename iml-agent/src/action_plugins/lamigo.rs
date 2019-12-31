// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::future::TryFutureExt;
use std::path::Path;
use std::process::Output;
use std::{fmt, io};
use tokio::fs;
use tokio::process::{Child, Command};

static SYSTEMD_DIR: &str = "/etc/systemd/system";

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

    #[structopt(long)]
    /// (Optional argument)
    /// By default, nothing is performed, if the mount point is already mounted.
    /// This flag is to force the mount execution.
    force: bool,
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
    if c.force {
        create_lamigo_service_unit_internal(SYSTEMD_DIR, &c)
            .err_into()
            .await
    } else {
        let is_mounted = is_filesystem_mounted(&c.mount_point).await?;
        if !is_mounted {
            mount_filesystem(&c).await?;
        }
        create_lamigo_service_unit_internal(SYSTEMD_DIR, &c).await?;
        Ok(())
    }
}

pub async fn mount_filesystem(c: &Config) -> std::io::Result<()> {
    // according to http://wiki.lustre.org/Mounting_a_Lustre_File_System_on_Client_Nodes
    // we need to execute mount command
    //   mount -t lustre \
    //     [-o <options> ] \
    //     <MGS NID>[:<MGS NID>]:/<fsname> \
    //     /lustre/<fsname>
    let process: Child = Command::new("mount")
        .arg("-t")
        .arg("lustre")
        .arg(c.lustre_device.clone())
        .arg(c.mount_point.clone())
        .spawn()?;
    let output: Output = process.wait_with_output().await?;
    match output.status.success() {
        true => Ok(()),
        false => Err(io::Error::new(
            io::ErrorKind::Other,
            format!(
                "Cannot execute command \'mount -t lustre {} {}\'",
                c.lustre_device, c.mount_point
            ),
        )),
    }
}

pub async fn is_filesystem_mounted(mount_point: &str) -> std::io::Result<bool> {
    // `mountpoint -q /mnt/something` produces no output,
    // but signals the caller with the exit code
    let process: Child = Command::new("mountpoint")
        .arg("-q")
        .arg(mount_point)
        .spawn()?;
    let output: Output = process.wait_with_output().await?;
    Ok(output.status.success())
}

async fn create_lamigo_service_unit_internal<P: AsRef<Path>>(
    dir: P,
    c: &Config,
) -> std::io::Result<()> {
    fs::create_dir_all(&dir).await?;
    let file = dir
        .as_ref()
        .join(format!("lamigo-{}-{}.service", c.fs, c.mdt));
    let cnt = format!("{}", c);
    fs::write(file, cnt.as_bytes()).await
}

#[cfg(test)]
mod lamigo_tests {
    use super::*;
    use insta::assert_display_snapshot;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_works() {
        // cargo run --package iml-agent --bin iml-agent -- lamigo
        // --cold_pool COLD_POOL --hot_pool HOT_POOL
        // --fs LU_TEST --lustre_device 192.168.0.100@tcp0:/spfs
        // --mdt MDT000 --min_age 10000 --user nick --mount_point /mnt/lustre
        let config = Config {
            fs: "lu_test".into(),
            mdt: "lustre-MDT0000".into(),
            user: "cl1".into(),
            min_age: 35353,
            mount_point: "/mnt/lustre".into(),
            lustre_device: "192.168.0.100@tcp0:/spfs".into(),
            hot_pool: "fast_pool".into(),
            cold_pool: "slow_pool".into(),
            force: true,
        };

        let dir = tempdir().expect("could not create tmpdir");
        let expected_file = dir.path().join("lamigo-lu_test-lustre-MDT0000.service");
        create_lamigo_service_unit_internal(&dir, &config)
            .await
            .expect("could not write ");

        let bytes = fs::read(expected_file).await.unwrap();
        let content = String::from_utf8_lossy(&bytes);
        assert_display_snapshot!(content);
    }
}
