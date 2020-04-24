// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::future::try_join_all;
use iml_cmd::{CheckedCommandExt, CmdError};
use std::{
    process::{Output, Stdio},
    str,
};
use tokio::{fs::canonicalize, io::AsyncWriteExt, process::Command};

pub async fn ssh_exec(host: &str, cmd: &str) -> Result<Output, CmdError> {
    println!("Running command {} on {}", cmd, host);
    let path = canonicalize("../vagrant/").await?;

    let mut x = Command::new("ssh");
    x.current_dir(path);

    x.arg("-i")
        .arg("id_rsa")
        .arg("-o")
        .arg("StrictHostKeyChecking=no")
        .arg(host)
        .arg(cmd);

    let out = x.checked_output().await?;

    Ok(out)
}

async fn ssh_exec_parallel(servers: &[&str], cmd: &str) -> Result<Vec<Output>, CmdError> {
    let remote_calls = servers.iter().map(|host| ssh_exec(host, cmd));

    let output = try_join_all(remote_calls).await?;

    for out in &output {
        println!(
            "{}",
            str::from_utf8(&out.stdout).expect("Couldn't read output.")
        );
    }

    Ok(output)
}

pub async fn ssh_script(host: &str, script: &str, args: &[&str]) -> Result<Output, CmdError> {
    let path = canonicalize("../vagrant/").await?;
    let mut script_path = path.clone();

    script_path.push(script);

    println!(
        "Executing script: {} on {}",
        script_path
            .clone()
            .into_os_string()
            .into_string()
            .expect("Couldn't convert path to string."),
        host
    );
    let script_content = iml_fs::read_file_to_end(script_path).await?;

    println!(
        "script content: {}",
        str::from_utf8(&script_content).expect("Couldn't get script content")
    );

    let mut x = Command::new("ssh");
    x.current_dir(path);

    let ssh_child = x
        .arg("-i")
        .arg("id_rsa")
        .arg("-o")
        .arg("StrictHostKeyChecking=no")
        .arg(host)
        .arg("bash -s")
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::inherit())
        .spawn()?;

    let mut ssh_stdin = ssh_child.stdin.unwrap();
    ssh_stdin.write_all(&script_content).await?;

    let out = x.checked_output().await?;

    Ok(out)
}

async fn ssh_script_parallel(
    servers: &[&str],
    script: &str,
    args: &[&str],
) -> Result<Vec<Output>, CmdError> {
    let remote_calls = servers.iter().map(|host| ssh_script(host, script, args));

    let output = try_join_all(remote_calls).await?;

    for out in &output {
        println!(
            "{}",
            str::from_utf8(&out.stdout).expect("Couldn't read output.")
        );
    }

    Ok(output)
}

pub async fn install_ldiskfs_no_iml(
    hosts: &[&str],
    lustre_version: &str,
) -> Result<Vec<Output>, CmdError> {
    ssh_script_parallel(
        hosts,
        "scripts/install_ldiskfs_no_iml.sh",
        &[lustre_version],
    )
    .await
}

pub async fn install_zfs_no_iml(
    hosts: &[&str],
    lustre_version: &str,
) -> Result<Vec<Output>, CmdError> {
    ssh_script_parallel(hosts, "scripts/install_zfs_no_iml.sh", &[lustre_version]).await
}

pub async fn yum_update(hosts: &[&str]) -> Result<Vec<Output>, CmdError> {
    ssh_exec_parallel(hosts, "yum clean metadata; yum update -y").await
}

pub async fn configure_ntp_for_host_only_if(hosts: &[&str]) -> Result<Vec<Output>, CmdError> {
    ssh_script_parallel(hosts, "scripts/configure_ntp.sh", &["10.73.10.1"]).await
}

pub async fn configure_ntp_for_adm(hosts: &[&str]) -> Result<Vec<Output>, CmdError> {
    ssh_script_parallel(hosts, "scripts/configure_ntp.sh", &["adm.local"]).await
}

pub async fn wait_for_ntp(hosts: &[&str]) -> Result<Vec<Output>, CmdError> {
    ssh_script_parallel(hosts, "scripts/wait_for_ntp.sh", &[]).await
}
