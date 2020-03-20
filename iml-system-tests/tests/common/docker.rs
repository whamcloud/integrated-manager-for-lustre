use crate::common::{iml, systemd, CheckedStatus};
use std::{io, process::ExitStatus, thread, time};
use tokio::{fs, process::Command};

const IML_DOCKER_PATH: &str = "/etc/iml-docker";

pub async fn docker() -> Result<Command, io::Error> {
    let mut x = Command::new("docker");

    let path = fs::canonicalize(IML_DOCKER_PATH).await?;

    x.current_dir(path);

    Ok(x)
}

pub async fn deploy_iml_stack() -> Result<(), io::Error> {
    systemd::start("iml-docker").await?.checked_status().await?;

    Ok(())
}

pub async fn remove_iml_stack() -> Result<Command, io::Error> {
    let mut x = docker().await?;

    x.arg("stack").arg("rm").arg("iml");

    Ok(x)
}

pub async fn volume_prune() -> Result<(), io::Error> {
    let mut x = docker().await?;

    x.arg("volume").arg("prune").checked_status().await?;

    Ok(())
}

pub async fn network_prune() -> Result<(), io::Error> {
    let mut x = docker().await?;

    x.arg("network").arg("prune").checked_status().await?;

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
