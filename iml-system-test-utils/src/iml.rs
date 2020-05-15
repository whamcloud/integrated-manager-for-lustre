// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::get_local_server_names;
use iml_cmd::{CheckedCommandExt, CmdError};
use tokio::{fs, process::Command};

pub const IML_DOCKER_PATH: &str = "/etc/iml-docker";
pub const IML_RPM_CONFIG_PATH: &str = "/var/lib/chroma";
pub const IML_AGENT_CONFIG_PATH: &str = "/etc/iml";

async fn iml() -> Result<Command, CmdError> {
    let mut x = Command::new("/usr/bin/iml");

    let path = fs::canonicalize(IML_DOCKER_PATH).await?;

    x.current_dir(path);

    Ok(x)
}

pub async fn list_servers() -> Result<Command, CmdError> {
    let mut x = iml().await?;

    x.arg("server").arg("list");

    Ok(x)
}

pub async fn server_add(host_map: &Vec<(String, &[&str])>) -> Result<(), CmdError> {
    for (profile, hosts) in host_map {
        let mut x = iml().await?;
        x.arg("server")
            .arg("add")
            .arg("-h")
            .arg(get_local_server_names(hosts).join(","))
            .arg("-p")
            .arg(profile)
            .checked_status()
            .await?;
    }

    Ok(())
}

pub async fn detect_fs() -> Result<(), CmdError> {
    let mut x = iml().await?;

    x.arg("filesystem").arg("detect").checked_status().await?;

    Ok(())
}
