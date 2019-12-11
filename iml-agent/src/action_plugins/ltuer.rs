// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use std::path::{Path, PathBuf};
use tokio::io::{AsyncWrite, AsyncWriteExt};
use tokio_fs as fs;

static CONFIGURATION_DIR: &str = "/etc/iml";

async fn create_ltuer_conf_internal<W>(
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

    writer
        .write(contents.as_bytes())
        .await
        .map(|_| ())
        .map_err(|e| e.into())
}

async fn wrap_file_creation<P>(
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

    create_ltuer_conf_internal((mailbox_path, fs_name, cold_pool), &mut file).await
}

pub async fn create_ltuer_conf(
    (mailbox_path, fs_name, cold_pool): (String, String, String),
) -> Result<(), ImlAgentError> {
    wrap_file_creation((mailbox_path, fs_name, cold_pool), CONFIGURATION_DIR).await
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_create_ltuer_conf() {
        let dir = tempdir().unwrap();

        wrap_file_creation(("foo".into(), "bar".into(), "baz".into()), dir.path())
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
