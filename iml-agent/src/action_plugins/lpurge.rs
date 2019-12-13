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
    #[structopt(long)]
    /// Filesystem name
    fs: String,
    #[structopt(long)]
    /// Object Storage Target name
    ost: String,
    #[structopt(long)]
    /// OST pool name
    pool: String,
    #[structopt(long)]
    freelo: u8,
    #[structopt(long)]
    freehi: u8,
}

impl fmt::Display for Config {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "\
             device={fs}-{ost}\n\
             dryrun=true\n\
             freehi={freehi}\n\
             freelo={freelo}\n\
             listen_socket=/run/lpurge-{fs}-{ost}-{pool}.sock\n\
             max_jobs=0\n\
             pool={fs}.{pool}\n\
             ",
            freehi = self.freehi,
            freelo = self.freelo,
            fs = self.fs,
            ost = self.ost,
            pool = self.pool,
        )
    }
}

pub async fn create_lpurge_conf(c: Config) -> Result<(), ImlAgentError> {
    write("/etc/lpurge", &c).err_into().await
}

async fn write<P: AsRef<Path>>(dir: P, c: &Config) -> std::io::Result<()> {
    fs::create_dir_all(&dir).await?;

    let file = dir.as_ref().join(format!("{}.conf", c.ost));
    let cnt = format!("{}", c);
    fs::write(file, cnt.as_bytes()).await
}

#[cfg(test)]
mod lpurge_conf_tests {
    use super::*;
    use insta::assert_display_snapshot;
    use tempfile::tempdir;

    #[tokio::test]
    async fn works() {
        let cfg = Config {
            fs: "lima".to_string(),
            pool: "santiago".to_string(),
            ost: "montevideo".to_string(),
            freehi: 123,
            freelo: 60,
        };

        let dir = tempdir().expect("could not create tmpdir");
        let expected_file = dir.path().join("montevideo.conf");

        write(&dir, &cfg).await.expect("could not write");

        let cnt = String::from_utf8(
            std::fs::read(&expected_file).expect(expected_file.to_str().unwrap()),
        )
        .unwrap();

        assert_display_snapshot!(cnt);
    }
}
