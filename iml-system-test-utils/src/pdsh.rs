// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_cmd::{CheckedCommandExt, CmdError};
use std::{process::Stdio, str};
use tokio::{
    fs::canonicalize,
    io::{AsyncReadExt, AsyncWriteExt},
    process::Command,
};

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
    let pdsh_child = x
        .arg("-S")
        .arg("-d")
        .arg("-t")
        .arg("100")
        .arg("-R")
        .arg("ssh")
        .arg("-u")
        .arg("root")
        .arg("-w")
        .arg(hosts.join(","))
        .arg(cmd)
        .stdout(Stdio::piped())
        .spawn()?;

    let mut dshbak = Command::new("dshbak");
    let dshbak_child = dshbak
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()?;

    let mut pdsh_out = pdsh_child.stdout.expect("Couldn't get stdout.");
    let mut dshbak_in = dshbak_child.stdin.expect("Couldn't get stdin.");

    let mut buf: Vec<u8> = Vec::new();
    pdsh_out.read_to_end(&mut buf).await?;
    dshbak_in.write_all(&buf).await?;

    Ok(dshbak)
}

async fn run_script_on_remote_hosts(hosts: &[&str], output: &[u8]) -> Result<(), CmdError> {
    let script = str::from_utf8(output).expect("Couldn't get output of script.");
    pdsh(&hosts, script).await?.checked_status().await?;

    Ok(())
}

pub async fn install_ldiskfs_no_iml(hosts: &[&str], lustre_version: &str) -> Result<(), CmdError> {
    let out = sed("../vagrant")
        .await?
        .arg(format!(r#"s/\$1/{}/"#, lustre_version))
        .arg("scripts/install_ldiskfs_no_iml.sh")
        .output()
        .await?;

    run_script_on_remote_hosts(&hosts, &out.stdout).await
}

pub async fn install_zfs_no_iml(hosts: &[&str], lustre_version: &str) -> Result<(), CmdError> {
    let out = sed("../vagrant")
        .await?
        .arg(format!(r#"s/\$1/{}/"#, lustre_version))
        .arg("scripts/install_zfs_no_iml.sh")
        .output()
        .await?;

    run_script_on_remote_hosts(&hosts, &out.stdout).await
}

pub async fn yum_update(hosts: &[&str]) -> Result<(), CmdError> {
    pdsh(&hosts, "yum clean metadata; yum update -y")
        .await?
        .checked_status()
        .await?;

    Ok(())
}

pub async fn configure_ntp_for_host_only_if(hosts: &[&str]) -> Result<(), CmdError> {
    let out = sed("../vagrant")
        .await?
        .arg(r#"s/\$1/10.73.10.1/"#)
        .arg("scripts/configure_ntp.sh")
        .output()
        .await?;

    run_script_on_remote_hosts(&hosts, &out.stdout).await
}

pub async fn configure_ntp_for_adm(hosts: &[&str]) -> Result<(), CmdError> {
    let out = sed("../vagrant")
        .await?
        .arg(r#"s/\$1/adm.local/"#)
        .arg("scripts/configure_ntp.sh")
        .output()
        .await?;

    run_script_on_remote_hosts(&hosts, &out.stdout).await
}

pub async fn wait_for_ntp_for_host_only_if(hosts: &[&str]) -> Result<(), CmdError> {
    let out = sed("../vagrant")
        .await?
        .arg(r#"s/\$1/10.73.10.1/"#)
        .arg("scripts/wait_for_ntp.sh")
        .output()
        .await?;

    run_script_on_remote_hosts(&hosts, &out.stdout).await
}

pub async fn wait_for_ntp_for_adm(hosts: &[&str]) -> Result<(), CmdError> {
    let out = sed("../vagrant")
        .await?
        .arg(r#"s/\$1/adm.local/"#)
        .arg("scripts/wait_for_ntp.sh")
        .output()
        .await?;

    run_script_on_remote_hosts(&hosts, &out.stdout).await
}
