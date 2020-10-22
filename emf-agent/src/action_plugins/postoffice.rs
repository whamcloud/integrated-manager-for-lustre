// Copyright (c) 2021 DDN. All rights reserved.
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
use crate::{agent_error::EmfAgentError, env};
use lazy_static::lazy_static;
use std::collections::BTreeSet;
use std::iter::FromIterator;
use tokio::{
    fs,
    io::AsyncWriteExt,
    time::{sleep, Duration},
};

lazy_static! {
    static ref POSTMAN_CONF: String = env::get_var("POSTMAN_CONF_PATH");
    static ref POSTMAN_CONF_NEW: String = format!("{}.new", *POSTMAN_CONF);
}

async fn write_config(mut file: fs::File, routes: BTreeSet<String>) -> Result<(), EmfAgentError> {
    let rt: Vec<String> = Vec::from_iter(routes);
    file.write_all(rt.join("\n").as_bytes()).await?;
    file.write(b"\n").await?;
    Ok(())
}

/// Open new file ${POSTMAN_CONF_PATH}.new or loop until we can
async fn lock_file() -> Result<fs::File, EmfAgentError> {
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
        sleep(delay).await;
    }
}

pub enum UnlockOp {
    Keep,
    Drop,
}

pub async fn unlock_file(op: UnlockOp) -> Result<(), EmfAgentError> {
    match op {
        UnlockOp::Keep => fs::rename(&*POSTMAN_CONF_NEW, &*POSTMAN_CONF).await?,
        UnlockOp::Drop => fs::remove_file(&*POSTMAN_CONF_NEW).await?,
    }
    Ok(())
}

async fn read_config() -> Result<BTreeSet<String>, EmfAgentError> {
    Ok(fs::read_to_string(&*POSTMAN_CONF)
        .await?
        .lines()
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .collect())
}

enum RouteOp {
    Insert,
    Remove,
}

async fn locked_route(
    file: fs::File,
    mailbox: String,
    action: RouteOp,
) -> Result<UnlockOp, EmfAgentError> {
    let mut conf = read_config().await?;

    let rc = match action {
        RouteOp::Insert => conf.insert(mailbox),
        RouteOp::Remove => conf.remove(&mailbox),
    };
    if rc {
        write_config(file, conf).await?;
        Ok(UnlockOp::Keep)
    } else {
        Ok(UnlockOp::Drop)
    }
}

pub async fn route_add(mailbox: String) -> Result<(), EmfAgentError> {
    let file = lock_file().await?;

    let (rename, rc) = match locked_route(file, mailbox, RouteOp::Insert).await {
        Ok(b) => (b, Ok(())),
        Err(e) => (UnlockOp::Drop, Err(e)),
    };

    unlock_file(rename).await?;
    rc
}

pub async fn route_remove(mailbox: String) -> Result<(), EmfAgentError> {
    let file = lock_file().await?;

    let (rename, rc) = match locked_route(file, mailbox, RouteOp::Remove).await {
        Ok(b) => (b, Ok(())),
        Err(e) => (UnlockOp::Drop, Err(e)),
    };

    unlock_file(rename).await?;
    rc
}
