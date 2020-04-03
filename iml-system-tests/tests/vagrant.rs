// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{future::BoxFuture, FutureExt, TryFutureExt};
use std::{env, io, process::ExitStatus};
use tokio::{fs, process::Command};

fn handle_status(x: ExitStatus) -> Result<(), io::Error> {
    if x.success() {
        Ok(())
    } else {
        let err = io::Error::new(
            io::ErrorKind::Other,
            format!("process exited with code: {:?}", x.code()),
        )
        .into();
        Err(err)
    }
}

trait CheckedStatus {
    fn checked_status(&mut self) -> BoxFuture<Result<(), io::Error>>;
}

impl CheckedStatus for Command {
    /// Similar to `status`, but returns `Err` if the exit code is non-zero.
    fn checked_status(&mut self) -> BoxFuture<Result<(), io::Error>> {
        println!("Running cmd: {:?}", self);

        self.status()
            .and_then(|x| async move { handle_status(x) })
            .boxed()
    }
}

async fn vagrant() -> Result<Command, io::Error> {
    let mut x = Command::new("vagrant");

    let path = fs::canonicalize("../vagrant").await?;

    x.current_dir(path);

    Ok(x)
}

pub async fn up<'a>() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("up");

    Ok(x)
}

pub async fn destroy<'a>() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("destroy").arg("-f");

    Ok(x)
}

pub async fn halt() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;
    x.arg("halt");

    Ok(x)
}

async fn snapshot() -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("snapshot");

    Ok(x)
}

pub async fn snapshot_save(host: &str, name: &str) -> Result<Command, io::Error> {
    let mut x = snapshot().await?;

    x.arg("save").arg(host).arg(name);

    Ok(x)
}

pub async fn snapshot_restore(host: &str, name: &str) -> Result<Command, io::Error> {
    let mut x = snapshot().await?;

    x.arg("restore").arg(host).arg(name);

    Ok(x)
}

pub async fn snapshot_delete(host: &str, name: &str) -> Result<Command, io::Error> {
    let mut x = snapshot().await?;

    x.arg("delete").arg(host).arg(name);

    Ok(x)
}

pub async fn provision(name: &str) -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("provision").arg("--provision-with").arg(name);

    Ok(x)
}

pub async fn run_vm_command(node: &str, cmd: &str) -> Result<Command, io::Error> {
    let mut x = vagrant().await?;

    x.arg("ssh").arg("-c").arg(&format!("{}", cmd)).arg(node);

    Ok(x)
}

pub async fn setup_bare(hosts: &[&str]) -> Result<(), Box<dyn std::error::Error>> {
    up().await?.args(hosts).checked_status().await?;

    provision("yum-update")
        .await?
        .args(hosts)
        .checked_status()
        .await?;

    halt().await?.args(hosts).checked_status().await?;

    for x in hosts {
        snapshot_save(x, "bare").await?.checked_status().await?;
    }

    up().await?.args(hosts).checked_status().await?;

    Ok(())
}

pub async fn setup_iml_install(hosts: &[&str]) -> Result<(), Box<dyn std::error::Error>> {
    setup_bare(hosts).await?;

    match env::var("REPO_URI") {
        Ok(x) => {
            provision("install-iml-repouri")
                .await?
                .env("REPO_URI", x)
                .checked_status()
                .await?;
        }
        _ => {
            provision("install-iml-local")
                .await?
                .args(hosts)
                .checked_status()
                .await?;
        }
    };

    halt().await?.args(hosts).checked_status().await?;

    for host in hosts {
        snapshot_save(host, "iml-installed")
            .await?
            .checked_status()
            .await?;
    }

    up().await?.args(hosts).checked_status().await?;

    Ok(())
}

pub async fn setup_deploy_servers(
    config: &ClusterConfig,
    profile: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    setup_iml_install(&config.all()).await?;

    run_vm_command(
        "adm",
        &format!(
            "iml server add -h {} -p {}",
            config.storage_servers().join(","),
            profile
        ),
    )
    .await?
    .checked_status()
    .await?;

    halt().await?.args(config.all()).checked_status().await?;

    for host in config.all() {
        snapshot_save(host, "iml-deployed")
            .await?
            .checked_status()
            .await?;
    }

    up().await?.args(config.all()).checked_status().await?;

    Ok(())
}

pub struct ClusterConfig {
    manager: &'static str,
    mds: Vec<&'static str>,
    oss: Vec<&'static str>,
    clients: Vec<&'static str>,
    iscsi: &'static str,
}

impl Default for ClusterConfig {
    fn default() -> Self {
        ClusterConfig {
            manager: "adm",
            mds: vec!["mds1", "mds2"],
            oss: vec!["oss1", "oss2"],
            clients: vec!["c1"],
            iscsi: "iscsi",
        }
    }
}

impl ClusterConfig {
    fn all(&self) -> Vec<&str> {
        let mut xs = vec![self.iscsi, self.manager];

        xs.extend(self.storage_servers());
        xs.extend(&self.clients);

        xs
    }
    fn storage_servers(&self) -> Vec<&str> {
        [&self.mds[..], &self.oss[..]].concat()
    }
}
