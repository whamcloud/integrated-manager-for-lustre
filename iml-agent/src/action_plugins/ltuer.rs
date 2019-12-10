// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use std::path::PathBuf;
use tokio_fs as fs;

static CONFIGURATION_DIR: &str = "/etc/iml";

pub async fn create_ltuer_conf(
    (mailbox_path, fs_name, cold_pool): (String, String, String),
) -> Result<(), ImlAgentError> {
    fs::create_dir_all(CONFIGURATION_DIR).await?;

    let contents = format!(
        "mailbox={}\nfs_name={}\ncold_pool={}\n",
        mailbox_path, fs_name, cold_pool
    );

    let mut path = PathBuf::from(CONFIGURATION_DIR);
    path.push("ltuer.conf");

    fs::write(path, contents).await.map_err(|e| e.into())
}

#[tokio::test]
async fn ltuer() {
    create_ltuer_conf(("foo".into(), "bar".into(), "baz".into()))
        .await
        .unwrap();
}
