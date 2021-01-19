// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::EmfAgentError, env};
use std::collections::BTreeSet;
use std::iter::FromIterator;
use tokio::{fs, io::AsyncWriteExt};

async fn write_config(routes: BTreeSet<String>) -> Result<(), EmfAgentError> {
    let conf_file = env::get_var("POSTMAN_CONF_PATH");
    let mut file = fs::File::create(conf_file).await?;
    let rt: Vec<String> = Vec::from_iter(routes);
    file.write_all(rt.join("\n").as_bytes()).await?;
    file.write(b"\n").await?;
    Ok(())
}

async fn read_config() -> Result<BTreeSet<String>, EmfAgentError> {
    let conf_file = env::get_var("POSTMAN_CONF_PATH");
    Ok(fs::read_to_string(conf_file)
        .await?
        .lines()
        .map(|s| s.to_string())
        .collect())
}

pub async fn route_add(mailbox: String) -> Result<(), EmfAgentError> {
    let mut conf = read_config().await?;
    if conf.insert(mailbox) {
        write_config(conf).await
    } else {
        Ok(())
    }
}

pub async fn route_remove(mailbox: String) -> Result<(), EmfAgentError> {
    let mut conf = read_config().await?;
    if conf.remove(&mailbox) {
        write_config(conf).await
    } else {
        Ok(())
    }
}
