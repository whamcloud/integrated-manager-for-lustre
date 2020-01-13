// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, daemon_plugins::postoffice::CONF_FILE};

use std::collections::HashSet;
use tokio::{fs, io::AsyncWriteExt};

async fn write_config(mut routes: HashSet<String>) -> Result<(), ImlAgentError> {
    let mut file = fs::File::create(CONF_FILE).await?;
    let rt: Vec<String> = routes.drain().collect();
    file.write_all(rt.join("\n").as_bytes()).await?;
    file.write(b"\n").await?;
    Ok(())
}

async fn read_config() -> Result<HashSet<String>, ImlAgentError> {
    Ok(fs::read_to_string(CONF_FILE)
        .await?
        .lines()
        .map(|s| s.to_string())
        .collect())
}

pub async fn route_add(mailbox: String) -> Result<(), ImlAgentError> {
    let mut conf = read_config().await?;
    if conf.insert(mailbox) {
        write_config(conf).await
    } else {
        Ok(())
    }
}

pub async fn route_remove(mailbox: String) -> Result<(), ImlAgentError> {
    let mut conf = read_config().await?;
    if conf.remove(&mailbox) {
        write_config(conf).await
    } else {
        Ok(())
    }
}
