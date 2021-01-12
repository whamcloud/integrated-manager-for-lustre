// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::*;
use futures::future::TryFutureExt;
use std::str;
use tokio::{fs::canonicalize, process::Command};

pub async fn vagrant() -> Result<Command, TestError> {
    let mut x = Command::new("vagrant");

    let path = canonicalize("../vagrant/").await?;

    x.current_dir(path);

    Ok(x)
}

pub async fn up<'a>() -> Result<Command, TestError> {
    let mut x = vagrant().await?;

    x.arg("up");

    Ok(x)
}

pub async fn destroy<'a>(config: &Config) -> Result<(), TestError> {
    let nodes = config.destroy_list();

    for node in &nodes {
        let mut suspend_cmd = suspend().await?;
        suspend_cmd.arg(node);

        try_command_n_times(3, 1, &mut suspend_cmd).await?;
    }

    for node in &nodes {
        let mut destroy_cmd = vagrant().await?;
        destroy_cmd.arg("destroy").arg("-f").arg(node);

        try_command_n_times(3, 1, &mut destroy_cmd).await?;
    }

    Ok(())
}

pub async fn halt() -> Result<Command, TestError> {
    let mut x = vagrant().await?;
    x.arg("halt");

    Ok(x)
}

pub async fn suspend() -> Result<Command, TestError> {
    let mut x = vagrant().await?;
    x.arg("suspend");

    Ok(x)
}

pub async fn reload() -> Result<Command, TestError> {
    let mut x = vagrant().await?;
    x.arg("reload");

    Ok(x)
}

async fn snapshot() -> Result<Command, TestError> {
    let mut x = vagrant().await?;

    x.arg("snapshot");

    Ok(x)
}

pub async fn snapshot_save(host: &str, name: &str) -> Result<Command, TestError> {
    let mut x = snapshot().await?;

    x.arg("save").arg("-f").arg(host).arg(name);

    Ok(x)
}

pub async fn snapshot_restore(host: &str, name: &str) -> Result<Command, TestError> {
    let mut x = snapshot().await?;

    x.arg("restore").arg(host).arg(name);

    Ok(x)
}

pub async fn snapshot_delete(host: &str, name: &str) -> Result<Command, TestError> {
    let mut x = snapshot().await?;

    x.arg("delete").arg("-f").arg(host).arg(name);

    Ok(x)
}

pub async fn provision(name: &str) -> Result<Command, TestError> {
    let mut x = vagrant().await?;

    x.arg("provision").arg("--provision-with").arg(name);

    Ok(x)
}

pub async fn provision_node(node: &str, name: &str) -> Result<Command, TestError> {
    let mut x = vagrant().await?;

    x.arg("provision")
        .arg(node)
        .arg("--provision-with")
        .arg(name);

    Ok(x)
}

pub async fn rsync(host: &str) -> Result<(), TestError> {
    let mut x = vagrant().await?;

    x.arg("rsync").arg(host).checked_status().err_into().await
}
