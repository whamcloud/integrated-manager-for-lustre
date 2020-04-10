// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::CmdError;
use std::str;
use tokio::{fs::canonicalize, process::Command};

// sed "s/\$1/2.12.4/" scripts/install_ldiskfs_no_iml.sh | pdsh -R ssh -u root -w 10.73.10.11,10.73.10.12

pub async fn sed(base_path: &str) -> Result<Command, CmdError> {
    let mut x = Command::new("sed");

    let path = canonicalize(base_path).await?;
    x.current_dir(path);

    Ok(x)
}

pub async fn pdsh(hosts: &[&str], cmd: &str) -> Result<Command, CmdError> {
    let mut x = Command::new("pdsh");

    let path = canonicalize("../vagrant/").await?;

    x.current_dir(path);
    x.env(
        "PDSH_SSH_ARGS_APPEND",
        "-i id_rsa -o StrictHostKeyChecking=no",
    );
    x.arg("-R")
        .arg("ssh")
        .arg("-u")
        .arg("root")
        .arg("-w")
        .arg(hosts.join(","))
        .arg(cmd);

    Ok(x)
}

pub async fn install_ldiskfs_no_iml(hosts: &[&str], lustre_version: &str) -> Result<(), CmdError> {
    let out = sed("../vagrant")
        .await?
        .arg(format!(r#"s/\$1/{}/"#, lustre_version))
        .arg("scripts/install_ldiskfs_no_iml.sh")
        .output()
        .await?;

    let script = str::from_utf8(&out.stdout)
        .expect("Couldn't get output of sed command on install_ldiskfs_no_iml.sh.");

    pdsh(&hosts, script).await?;

    Ok(())
}
