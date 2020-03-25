// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{try_command_n_times, CheckedStatus};
use std::io;
use tokio::{fs, process::Command};

const IML_DOCKER_PATH: &str = "/etc/iml-docker";

async fn iml() -> Result<Command, io::Error> {
    let mut x = Command::new("/usr/bin/iml");

    let path = fs::canonicalize(IML_DOCKER_PATH).await?;

    x.current_dir(path);

    Ok(x)
}

pub async fn list_servers() -> Result<Command, io::Error> {
    let mut x = iml().await?;

    x.arg("server").arg("list");

    Ok(x)
}

pub async fn server_add(hosts: &[&str], profile: &str) -> Result<(), io::Error> {
    let mut x = iml().await?;

    let mut r = x
        .arg("server")
        .arg("add")
        .arg("-h")
        .arg(hosts.join(","))
        .arg("-p")
        .arg(profile);

    try_command_n_times(3, &mut r).await?;

    Ok(())
}

pub async fn detect_fs() -> Result<(), io::Error> {
    let mut x = iml().await?;

    x.arg("filesystem").arg("detect").checked_status().await?;

    Ok(())
}
