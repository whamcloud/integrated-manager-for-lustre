// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use futures_util::future::TryFutureExt;
use std::path::{Path, PathBuf};
use tokio::{
    fs,
    io::{AsyncWrite, AsyncWriteExt},
};

static CONFIGURATION_DIR: &str = "/etc/iml";

async fn write_ltuer_conf<W>(
    (mailbox_path, fs_name, cold_pool): (String, String, String),
    writer: &mut W,
) -> Result<(), ImlAgentError>
where
    W: AsyncWrite + Unpin,
{
    let contents = format!(
        "mailbox={}\nfs_name={}\ncold_pool={}\n",
        mailbox_path, fs_name, cold_pool
    );

    writer.write(contents.as_bytes()).err_into().await.map(drop)
}

async fn create_ltuer_conf_internal<P>(
    (mailbox_path, fs_name, cold_pool): (String, String, String),
    dir_path: P,
) -> Result<(), ImlAgentError>
where
    P: AsRef<Path>,
    PathBuf: From<P>,
{
    fs::create_dir_all(&dir_path).await?;

    let mut path = PathBuf::from(dir_path);
    path.push("ltuer.conf");

    let mut file = fs::File::create(path).await?;

    write_ltuer_conf((mailbox_path, fs_name, cold_pool), &mut file).await
}

pub async fn create_ltuer_conf(
    (mailbox_path, fs_name, cold_pool): (String, String, String),
) -> Result<(), ImlAgentError> {
    create_ltuer_conf_internal((mailbox_path, fs_name, cold_pool), CONFIGURATION_DIR).await
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_create_ltuer_conf() {
        let dir = tempdir().unwrap();

        create_ltuer_conf_internal(("foo".into(), "bar".into(), "baz".into()), dir.path())
            .await
            .unwrap();

        let path = dir.path().join("ltuer.conf");

        let contents = fs::read(path).await.unwrap();
        assert_eq!(
            String::from_utf8_lossy(&contents),
            "mailbox=foo\nfs_name=bar\ncold_pool=baz\n"
        );
    }
}
