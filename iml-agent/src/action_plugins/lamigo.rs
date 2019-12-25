// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::future::TryFutureExt;
use std::fmt;
use std::path::Path;
use tokio::fs;

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
    /// Lustre client mount point, e.g. /mnt/lustre
    mount_point: String,
}

impl fmt::Display for Config {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f,
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

pub async fn create_lamigo_service(c: Config) -> Result<(), ImlAgentError> {
    create_lamigo_service_internal("/etc/systemd/system", &c).err_into().await
}

async fn create_lamigo_service_internal<P: AsRef<Path>>(dir: P, c: &Config) -> std::io::Result<()> {
    fs::create_dir_all(&dir).await?;
    let file = dir
        .as_ref()
        .join(format!("lamigo-{}-{}.service", c.fs, c.mdt));
    let cnt = format!("{}", c);
    fs::write(file, cnt.as_bytes()).await
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_create_lamigo_service() {
        let config = Config {
            fs: "lu_test".into(),
            mdt: "lustre-MDT0000".into(),
            user: "cl1".into(),
            min_age: 35353,
            mount_point: "/mnt/lustre".into(),
            hot_pool: "fast_pool".into(),
            cold_pool: "slow_pool".into(),
        };

        let dir = tempdir().expect("could not create tmpdir");
        let expected_file = dir.path().join("lamigo-lu_test-lustre-MDT0000.service");
        create_lamigo_service_internal(&dir, &config).await.expect("could not write ");

        let contents = fs::read(expected_file).await.unwrap();
        assert_eq!(
            String::from_utf8_lossy(&contents),
            "[Unit]\n\
            Description=Run lamigo service\n\
            [Service]\n\
            ExecStart=/usr/bin/lamigo -m lu_test-lustre-MDT0000 -u cl1 -s fast_pool -t slow_pool -a 35353 /mnt/lustre\n"
        );
    }
}
