// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use std::path::PathBuf;
use tokio::io::{AsyncWrite, AsyncWriteExt};
use tokio_fs as fs;

#[cfg(not(test))]
static CONFIGURATION_DIR: &str = "/etc/iml";
#[cfg(test)]
static CONFIGURATION_DIR: &str = "/tmp/etc/iml";

async fn create_ltuer_conf_internal<W>(
    (mailbox_path, fs_name, cold_pool): (String, String, String),
    writer: &mut W,
) -> Result<(), ImlAgentError>
where
    W: AsyncWrite + Unpin,
{
    fs::create_dir_all(CONFIGURATION_DIR).await?;

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

pub async fn create_ltuer_conf(
    (mailbox_path, fs_name, cold_pool): (String, String, String),
) -> Result<(), ImlAgentError> {
    fs::create_dir_all(CONFIGURATION_DIR).await?;

    let mut path = PathBuf::from(CONFIGURATION_DIR);
    path.push("ltuer.conf");

    let mut file = fs::File::create(path).await?;

    create_ltuer_conf_internal((mailbox_path, fs_name, cold_pool), &mut file).await
}

// Warning: only one test at a time can be executing,
// because they write to the same one file
#[tokio::test]
async fn test_create_ltuer_conf() {
    create_ltuer_conf(("foo".into(), "bar".into(), "baz".into()))
        .await
        .unwrap();

    let mut path = PathBuf::from(CONFIGURATION_DIR);
    path.push("ltuer.conf");

    let contents = fs::read(path).await.unwrap();
    assert_eq!(
        String::from_utf8_lossy(&contents),
        "mailbox=foo\nfs_name=bar\ncold_pool=baz\n"
    );
}
