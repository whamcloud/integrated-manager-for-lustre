// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env};
use futures_util::future::TryFutureExt;
use std::path::{Path, PathBuf};
use tokio::{
    fs,
    io::{AsyncWrite, AsyncWriteExt},
};

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
    path: P,
) -> Result<(), ImlAgentError>
where
    P: AsRef<Path>,
    PathBuf: From<P>,
{
    if let Some(dir_path) = path.as_ref().parent() {
        fs::create_dir_all(&dir_path).await?;
    }

    let mut file = fs::File::create(path).await?;

    write_ltuer_conf((mailbox_path, fs_name, cold_pool), &mut file).await
}

pub async fn create_ltuer_conf(
    (mailbox_path, fs_name, cold_pool): (String, String, String),
) -> Result<(), ImlAgentError> {
    let path = env::get_var("LTUER_CONF_PATH");

    create_ltuer_conf_internal((mailbox_path, fs_name, cold_pool), path).await
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_create_ltuer_conf() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("ltuer.conf");

        create_ltuer_conf_internal(("foo".into(), "bar".into(), "baz".into()), &path)
            .await
            .unwrap();

        let contents = fs::read(path).await.unwrap();
        assert_eq!(
            String::from_utf8_lossy(&contents),
            "mailbox=foo\nfs_name=bar\ncold_pool=baz\n"
        );
    }
}
