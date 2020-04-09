use crate::{
    iml::IML_DOCKER_PATH, SetupConfig, SetupConfigType, STRATAGEM_CLIENT_PROFILE,
    STRATAGEM_SERVER_PROFILE,
};
use iml_cmd::{CheckedCommandExt, CmdError};
use iml_systemd::SystemdError;
use std::{io, str};
use tokio::{
    fs::{canonicalize, File},
    io::AsyncWriteExt,
    process::Command,
};

pub async fn docker() -> Result<Command, io::Error> {
    let mut x = Command::new("docker");

    let path = canonicalize(IML_DOCKER_PATH).await?;

    x.current_dir(path);

    Ok(x)
}

pub async fn deploy_iml_stack() -> Result<(), SystemdError> {
    iml_systemd::start_unit_and_wait("iml-docker.service".into(), 400).await
}

pub async fn get_docker_service_count() -> Result<usize, io::Error> {
    let mut x = docker().await?;

    let services = x.arg("service").arg("ls").output().await?;

    let output = str::from_utf8(&services.stdout).expect("Couldn't read docker service list.");
    let cnt = output.lines().skip(1).count(); // subtract the header

    Ok(cnt)
}

pub async fn remove_iml_stack() -> Result<(), iml_systemd::SystemdError> {
    iml_systemd::stop_unit("iml-docker.service".into()).await
}

pub async fn system_prune() -> Result<(), CmdError> {
    let mut x = docker().await?;

    x.arg("system")
        .arg("prune")
        .arg("--force")
        .arg("--all")
        .checked_status()
        .await
}

pub async fn volume_prune() -> Result<(), CmdError> {
    let mut x = docker().await?;

    x.arg("volume")
        .arg("prune")
        .arg("--force")
        .checked_status()
        .await
}

pub async fn stop_swarm() -> Result<(), io::Error> {
    let mut x = docker().await?;

    x.arg("swarm").arg("leave").arg("--force").status().await?;

    Ok(())
}

pub async fn start_swarm() -> Result<(), CmdError> {
    let mut x = docker().await?;

    x.arg("swarm")
        .arg("init")
        .arg("--advertise-addr=127.0.0.1")
        .arg("--listen-addr=127.0.0.1")
        .checked_status()
        .await
}

pub async fn set_password() -> Result<(), CmdError> {
    let mut path = canonicalize(IML_DOCKER_PATH).await?;
    path.push("setup");
    path.push("password");

    let mut file = File::create(&path).await?;
    file.write_all(b"lustre").await?;

    let mut x = docker().await?;
    x.arg("secret")
        .arg("create")
        .arg("iml_pw")
        .arg(&path.to_str().expect("Couldn't convert password path"))
        .checked_status()
        .await
}

pub async fn remove_password() -> Result<(), io::Error> {
    let mut x = docker().await?;

    x.arg("secret").arg("rm").arg("iml_pw").status().await?;

    Ok(())
}

pub async fn configure_docker_setup(setup: &SetupConfigType) -> Result<(), io::Error> {
    let config: String = setup.into();
    let mut path = canonicalize(IML_DOCKER_PATH).await?;
    path.push("setup");

    let mut config_path = path.clone();
    config_path.push("config");

    let mut file = File::create(config_path).await?;
    file.write_all(config.as_bytes()).await?;

    let setup_config: &SetupConfig = setup.into();
    if setup_config.use_stratagem {
        let mut server_profile_path = path.clone();
        server_profile_path.push("stratagem-server.profile");

        let mut file = File::create(server_profile_path).await?;
        file.write_all(STRATAGEM_SERVER_PROFILE.as_bytes()).await?;

        let mut client_profile_path = path.clone();
        client_profile_path.push("stratagem-client.profile");

        let mut file = File::create(client_profile_path).await?;
        file.write_all(STRATAGEM_CLIENT_PROFILE.as_bytes()).await?;
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
  device:
    environment:
      - RUST_LOG=debug
"#;

    let mut path = canonicalize(IML_DOCKER_PATH).await?;
    path.push("docker-compose.overrides.yml");

    let mut file = File::create(path).await?;
    file.write_all(overrides.as_bytes()).await?;

    Ok(())
}
