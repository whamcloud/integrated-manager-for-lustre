use crate::{iml, CheckedStatus};
use iml_systemd;
use std::{io, thread, time};
use tokio::{
    fs::{canonicalize, File},
    io::AsyncWriteExt,
    process::Command,
};

const IML_DOCKER_PATH: &str = "/etc/iml-docker";

pub async fn docker() -> Result<Command, io::Error> {
    let mut x = Command::new("docker");

    let path = canonicalize(IML_DOCKER_PATH).await?;

    x.current_dir(path);

    Ok(x)
}

pub async fn deploy_iml_stack() -> Result<(), io::Error> {
    iml_systemd::start_unit_with_time("iml-docker.service".into(), 400).await?;

    Ok(())
}

pub async fn remove_iml_stack() -> Result<Command, io::Error> {
    iml_systemd::stop_unit("iml-docker.service".into()).await?;

    let mut x = docker().await?;

    x.arg("stack").arg("rm").arg("iml");

    Ok(x)
}

pub async fn system_prune() -> Result<(), io::Error> {
    let mut x = docker().await?;

    x.arg("system")
        .arg("prune")
        .arg("--force")
        .arg("--all")
        .checked_status()
        .await?;

    Ok(())
}

pub async fn volume_prune() -> Result<(), io::Error> {
    let mut x = docker().await?;

    x.arg("volume")
        .arg("prune")
        .arg("--force")
        .checked_status()
        .await?;

    Ok(())
}

pub async fn iml_stack_loaded() -> Result<bool, io::Error> {
    let x = iml::list_servers().await?.status().await?;

    Ok(x.success())
}

pub async fn wait_for_iml_stack() -> Result<(), io::Error> {
    let mut x = iml_stack_loaded().await?;

    while !x {
        let one_sec = time::Duration::from_millis(1000);

        thread::sleep(one_sec);

        x = iml_stack_loaded().await?;
    }

    Ok(())
}

pub async fn configure_docker_overrides() -> Result<(), io::Error> {
    let overrides = r#"version: "3.7"

services:
  job-scheduler:
    extra_hosts:
      - "mds1.local:10.73.10.11"
      - "mds2.local:10.73.10.12"
      - "oss1.local:10.73.10.21"
      - "oss2.local:10.73.10.22"
      - "c1.local:10.73.10.31"
    environment:
      - "NTP_SERVER_HOSTNAME=10.73.10.1"
  iml-warp-drive:
    environment:
      - RUST_LOG=debug
  iml-action-runner:
    environment:
      - RUST_LOG=debug
  iml-api:
    environment:
      - RUST_LOG=debug
  iml-ostpool:
    environment:
      - RUST_LOG=debug
  iml-stats:
    environment:
      - RUST_LOG=debug
  iml-agent-comms:
    environment:
      - RUST_LOG=debug
  device-aggregator:
    environment:
      - RUST_LOG=debug
"#;

    let mut path = canonicalize(IML_DOCKER_PATH).await?;
    path.push("docker-compose.overrides.yml");

    let mut file = File::create(path).await?;
    file.write_all(overrides.as_bytes()).await?;

    Ok(())
}