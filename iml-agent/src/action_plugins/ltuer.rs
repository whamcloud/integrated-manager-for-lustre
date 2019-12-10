// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::agent_error::ImlAgentError;
use tokio_fs as fs;

pub async fn create_ltuer_conf(
    (mailbox_path, fs_name, cold_pool): (String, String, String),
) -> Result<(), ImlAgentError> {
    fs::create_dir_all("/etc/iml").await?;

    let contents = format!(
        "mailbox={}
fs_name={}
cold_pool={}
",
        mailbox_path, fs_name, cold_pool
    );
    fs::write("/etc/iml/ltuer.conf", contents)
        .await
        .map_err(|e| e.into())
}

#[tokio::test]
async fn ltuer() {
    create_ltuer_conf(("foo".into(), "bar".into(), "baz".into())).await.unwrap();
}
