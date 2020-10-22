// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

/// File "locking"
///
/// Create ${POSTMAN_CONF_PATH}.new or loop until it's created.
/// Then read ${POSTMAN_CONF_PATH} and update (insert/remove mailbox).
/// if added/removed -> Write new list to ${POSTMAN_CONF_PATH}.new.
/// if added/removed -> move ${POSTMAN_CONF_PATH}.new over ${POSTMAN_CONF_PATH}
/// or else unlink ${POSTMAN_CONF_PATH}.new.
///
/// The rename operation is atomic, and thus the daemon plugin will only
/// ever get a fully formed file.
/// The create of the ".new" file act as mutex for other writers, before they read the main file.
use crate::{agent_error::ImlAgentError, env};
use lazy_static::lazy_static;
use std::collections::BTreeSet;
use std::iter::FromIterator;
use tokio::{
    fs,
    io::AsyncWriteExt,
    time::{delay_for, Duration},
};

lazy_static! {
    static ref POSTMAN_CONF: String = env::get_var("POSTMAN_CONF_PATH");
    static ref POSTMAN_CONF_NEW: String = format!("{}.new", *POSTMAN_CONF);
}

async fn write_config(mut file: fs::File, routes: BTreeSet<String>) -> Result<(), ImlAgentError> {
    let rt: Vec<String> = Vec::from_iter(routes);
    file.write_all(rt.join("\n").as_bytes()).await?;
    file.write(b"\n").await?;
    Ok(())
}

/// Open new file ${POSTMAN_CONF_PATH}.new or loop until we can
async fn lock_file() -> Result<fs::File, ImlAgentError> {
    let delay = Duration::new(1, 0);
    loop {
        match fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&*POSTMAN_CONF_NEW)
            .await
        {
            Ok(f) => break Ok(f),
            Err(e) => {
                if e.kind() != std::io::ErrorKind::AlreadyExists {
                    break Err(e.into());
                }
            }
        }
        tracing::trace!("Postman config lock file already exists");
        delay_for(delay).await;
    }
}

async fn unlock_file(rename: bool) -> Result<(), ImlAgentError> {
    if rename {
        fs::rename(&*POSTMAN_CONF_NEW, &*POSTMAN_CONF).await?;
    } else {
        fs::remove_file(&*POSTMAN_CONF_NEW).await?;
    }
    Ok(())
}

async fn read_config() -> Result<BTreeSet<String>, ImlAgentError> {
    Ok(fs::read_to_string(&*POSTMAN_CONF)
        .await?
        .lines()
        .map(|s| s.to_string())
        .collect())
}

async fn locked_route(
    file: fs::File,
    mailbox: String,
    insert: bool,
) -> Result<bool, ImlAgentError> {
    let mut conf = read_config().await?;

    let rc = if insert {
        conf.insert(mailbox)
    } else {
        conf.remove(&mailbox)
    };
    if rc {
        write_config(file, conf).await?;
        Ok(true)
    } else {
        Ok(false)
    }
}

pub async fn route_add(mailbox: String) -> Result<(), ImlAgentError> {
    let file = lock_file().await?;

    let (rename, rc) = match locked_route(file, mailbox, true).await {
        Ok(b) => (b, Ok(())),
        Err(e) => (false, Err(e)),
    };

    unlock_file(rename).await?;
    rc
}

pub async fn route_remove(mailbox: String) -> Result<(), ImlAgentError> {
    let file = lock_file().await?;

    let (rename, rc) = match locked_route(file, mailbox, false).await {
        Ok(b) => (b, Ok(())),
        Err(e) => (false, Err(e)),
    };

    unlock_file(rename).await?;
    rc
}
