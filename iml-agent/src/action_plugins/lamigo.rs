// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures::future::TryFutureExt;
use std::fmt;
use std::path::Path;
use tokio::fs;

#[derive(serde::Deserialize, structopt::StructOpt, Debug)]
pub struct Config {
    /// File system name
    #[structopt(long)]
    fs_name: String,

    /// Metadata target name
    #[structopt(long)]
    mdt_name: String,

    /// Cold pool name
    #[structopt(long)]
    cold_pool: String,

    /// Hot pool name
    #[structopt(long)]
    hot_pool: String,

    /// Minimum age
    #[structopt(long)]
    min_age: u32,

    /// Changelog user name
    #[structopt(long)]
    changelog_user_name: String,

    /// Mount point
    #[structopt(long)]
    mount_point: String,
}

impl fmt::Display for Config {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // lamigo -a <MIN_AGE> -m <FS_NAME>-<MDT_NAME> -u <CHANGELOG_USER_NAME> -t <COLD_POOL> -s <HOT_POOL> <MNT_PNT>
        write!(f,
               "\
               [Unit]
               Description=Run lamigo service
               [Service]
               Environment="SCRIPT_ARGS=%I"
               ExecStart=lamigo $SCRIPT_ARGS
               ",
               fs_name = self.fs_name,
               mdt_name = self.mdt_name,
               cold_pool = self.cold_pool,
               hot_pool = self.hot_pool,
               min_age = self.min_age,
               changelog_user_name = self.changelog_user_name,
               mount_point = self.mount_point,
        )
    }
}

pub async fn create_lamigo_service(c: Config) -> Result<(), ImlAgentError> {

}

//pub async fn create_lpurge_conf(c: Config) -> Result<(), ImlAgentError> {
//    write("/etc/lpurge", &c).err_into().await
//}
//
//async fn write<P: AsRef<Path>>(dir: P, c: &Config) -> std::io::Result<()> {
//    fs::create_dir_all(&dir).await?;
//
//    let file = dir.as_ref().join(format!("{}.conf", c.ost));
//    let cnt = format!("{}", c);
//    fs::write(file, cnt.as_bytes()).await
//}

mod test {

}
