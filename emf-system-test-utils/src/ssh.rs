// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.
use crate::{Config, TestError, TestType};
use emf_cmd::{CheckedChildExt, CheckedCommandExt};
use emf_graphql_queries::Query;
use futures::future::{try_join_all, TryFutureExt};
use std::{
    process::{Output, Stdio},
    str,
    time::{SystemTime, UNIX_EPOCH},
};
use tokio::{fs::canonicalize, io::AsyncWriteExt, process::Command};

pub async fn scp(from: String, to: String) -> Result<(), TestError> {
    tracing::debug!("transferring file from {} to {}", from, to);

    let path = canonicalize("../vagrant/").await?;

    let mut x = Command::new("scp");
    x.current_dir(path);

    x.arg("-o")
        .arg("StrictHostKeyChecking=no")
        .arg("-o")
        .arg("UserKnownHostsFile=/dev/null")
        .arg("-i")
        .arg("./id_rsa")
        .arg(from)
        .arg(to)
        .checked_status()
        .await?;

    Ok(())
}

pub async fn scp_down_parallel(
    servers: &[&str],
    remote_path: &str,
    to: &str,
) -> Result<(), TestError> {
    let remote_calls = servers.iter().map(|host| {
        let from = format!("{}:{}", host, remote_path);
        scp(from, to.to_string())
    });

    try_join_all(remote_calls).await?;

    Ok(())
}

pub async fn scp_up_parallel(
    servers: &[&str],
    from: &str,
    to_remote: &str,
) -> Result<(), TestError> {
    let remote_calls = servers.iter().map(|host| {
        let to = format!("{}:{}", host, to_remote);
        scp(from.into(), to)
    });

    try_join_all(remote_calls).await?;

    Ok(())
}

pub async fn ssh_exec_cmd<'a, 'b>(host: &'a str, cmd: &'b str) -> Result<Command, TestError> {
    tracing::debug!("Running command {} on {}", cmd, host);
    let path = canonicalize("../vagrant/").await?;

    let mut x = Command::new("ssh");
    x.current_dir(path);

    x.arg("-o")
        .arg("StrictHostKeyChecking=no")
        .arg("-o")
        .arg("UserKnownHostsFile=/dev/null")
        .arg("-i")
        .arg("id_rsa")
        .arg(host)
        .arg(cmd);

    Ok(x)
}

pub async fn ssh_exec<'a, 'b>(host: &'a str, cmd: &'b str) -> Result<(&'a str, Output), TestError> {
    let mut cmd = ssh_exec_cmd(host, cmd).await?;

    let out = cmd.checked_output().await?;

    Ok((host, out))
}

async fn ssh_exec_parallel<'a, 'b>(
    servers: &[&'a str],
    cmd: &'b str,
) -> Result<Vec<(&'a str, Output)>, TestError> {
    let remote_calls = servers.iter().map(|host| ssh_exec(host, cmd));

    let output = try_join_all(remote_calls).await?;

    for (host, out) in &output {
        tracing::debug!(
            "ssh output {}: {}",
            host,
            str::from_utf8(&out.stdout).expect("Couldn't read output.")
        );
    }

    Ok(output)
}

pub async fn ssh_script<'a, 'b>(
    host: &'a str,
    script: &'b str,
    args: &[&'b str],
) -> Result<(&'a str, Output), TestError> {
    let path = canonicalize("../vagrant/").await?;

    let mut script_path = path.clone();
    script_path.push(script);

    let script_content = emf_fs::read_file_to_end(script_path).await?;

    let mut x = Command::new("ssh");
    x.current_dir(path);

    let mut ssh_child = x
        .arg("-i")
        .arg("id_rsa")
        .arg("-o")
        .arg("StrictHostKeyChecking=no")
        .arg("-o")
        .arg("UserKnownHostsFile=/dev/null")
        .arg(host)
        .arg("bash -s")
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::inherit())
        .spawn()?;

    let ssh_stdin = ssh_child.stdin.as_mut().unwrap();
    ssh_stdin.write_all(&script_content).await?;

    let out = ssh_child.wait_with_checked_output().await?;

    Ok((host, out))
}

async fn ssh_script_parallel<'a, 'b>(
    servers: &'b [&'a str],
    script: &'b str,
    args: &[&'b str],
) -> Result<Vec<(&'a str, Output)>, TestError> {
    let remote_calls = servers.iter().map(|host| ssh_script(host, script, args));

    let output = try_join_all(remote_calls).await?;

    for (host, out) in &output {
        tracing::debug!(
            "ssh output {}: {}",
            host,
            str::from_utf8(&out.stdout).expect("Couldn't read output.")
        );
    }

    Ok(output)
}

pub async fn install_ldiskfs_no_emf(config: &Config) -> Result<Vec<(&str, Output)>, TestError> {
    ssh_script_parallel(
        &config.storage_server_ips(),
        "scripts/install_ldiskfs_no_emf.sh",
        &[config.lustre_version()],
    )
    .await
}

pub async fn yum_update<'a, 'b>(hosts: &'b [&'a str]) -> Result<Vec<(&'a str, Output)>, TestError> {
    ssh_exec_parallel(hosts, "yum clean metadata; yum update -y").await
}

pub async fn configure_ntp<'a, 'b>(
    test_type: TestType,
    manager: &str,
    hosts: &'b [&'a str],
) -> Result<Vec<(&'a str, Output)>, TestError> {
    if test_type == TestType::Docker {
        ssh_script(manager, "scripts/install_ntp.sh", &[]).await?;
    }

    ssh_script_parallel(hosts, "scripts/configure_ntp.sh", &["adm.local"]).await
}

pub async fn wait_for_ntp<'a, 'b>(
    hosts: &'b [&'a str],
) -> Result<Vec<(&'a str, Output)>, TestError> {
    ssh_script_parallel(hosts, "scripts/wait_for_ntp.sh", &["adm.local"]).await
}

pub async fn enable_debug_on_hosts<'a, 'b>(
    hosts: &'b [&'a str],
) -> Result<Vec<(&'a str, Output)>, TestError> {
    ssh_script_parallel(hosts, "scripts/enable_debug.sh", &[]).await
}

pub async fn create_emf_diagnostics<'a, 'b>(
    hosts: Vec<&'a str>,
    prefix: &'a str,
) -> Result<(), TestError> {
    let path_buf = canonicalize("../vagrant/").await?;
    let path = path_buf.as_path().to_str().expect("Couldn't get path.");

    tracing::debug!("Creating diagnostics on: {:?}", hosts);
    ssh_script_parallel(&hosts, "scripts/create_emf_diagnostics.sh", &[prefix]).await?;

    let now = SystemTime::now();
    let ts = now.duration_since(UNIX_EPOCH).unwrap().as_millis();

    let report_dir = format!("sosreport_{}_{}", prefix, ts);
    let mut mkdir = Command::new("mkdir");

    mkdir
        .current_dir(path)
        .arg(&report_dir)
        .checked_status()
        .await?;

    scp_down_parallel(
        &hosts,
        "/var/tmp/*sosreport*.tar.xz",
        format!("./{}/", &report_dir).as_str(),
    )
    .await?;

    let mut chmod = Command::new("chmod");
    chmod
        .current_dir(path)
        .arg("777")
        .arg("-R")
        .arg(report_dir)
        .checked_status()
        .err_into()
        .await
}

pub async fn detect_fs(host: &str) -> Result<(), TestError> {
    ssh_exec_cmd(host, "emf filesystem detect")
        .await?
        .checked_status()
        .err_into()
        .await
}

pub async fn list_fs_json(host: &str) -> Result<Vec<serde_json::Value>, TestError> {
    ssh_exec_cmd(host, "emf filesystem list --display json")
        .await?
        .checked_output()
        .err_into()
        .await
        .map(|o| serde_json::from_slice::<Vec<serde_json::Value>>(&o.stdout).unwrap())
}

pub async fn systemd_status(host: &str, service_name: &str) -> Result<Command, TestError> {
    let cmd = ssh_exec_cmd(host, format!("systemctl status {}", service_name).as_str()).await?;

    Ok(cmd)
}

pub async fn add_servers(host: &str, profile: &str, hosts: Vec<String>) -> Result<(), TestError> {
    ssh_exec_cmd(
        host,
        &format!("emf server add {} -p {}", hosts.join(","), profile),
    )
    .await?
    .checked_status()
    .await?;

    Ok(())
}

pub async fn graphql_call<T: serde::Serialize, R: serde::de::DeserializeOwned>(
    config: &Config,
    query: &Query<T>,
) -> Result<R, TestError> {
    let body = serde_json::to_string(query)?;
    let body = body.as_bytes();

    let mut ssh_child = ssh_exec_cmd(config.manager_ip, "emf debugql -")
        .await?
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;

    let ssh_stdin = ssh_child.stdin.as_mut().expect("Could not get stdin");
    ssh_stdin.write_all(body).await?;

    let out = ssh_child.wait_with_checked_output().await?;

    let stdout = String::from_utf8_lossy(&out.stdout);
    let stderr = String::from_utf8_lossy(&out.stderr);

    if !out.status.success() {
        return Err(TestError::Assert(format!(
            "Error during graphql_call. Code: {:?}, Output: {}, Error: {}",
            out.status.code(),
            &stdout,
            &stderr
        )));
    }

    tracing::debug!(
        "Graphql Resp: Code: {:?}, Output; {}, Error: {}",
        out.status.code(),
        stdout,
        stderr
    );

    let x = serde_json::from_str(&stdout)?;

    Ok(x)
}
