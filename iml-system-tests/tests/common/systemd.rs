use crate::common::iml;
use std::{io, process::ExitStatus, thread, time};
use tokio::{fs, process::Command};

const IML_DOCKER_PATH: &str = "/etc/iml-docker";

async fn systemctl() -> Result<Command, io::Error> {
    let mut x = Command::new("systemctl");

    Ok(x)
}

pub async fn start(service: &str) -> Result<Command, io::Error> {
    let mut x = systemctl().await?;

    x.arg("start").arg(service);

    Ok(x)
}

pub async fn stop(service: &str) -> Result<Command, io::Error> {
    let mut x = systemctl().await?;

    x.arg("stop").arg(service);

    Ok(x)
}
