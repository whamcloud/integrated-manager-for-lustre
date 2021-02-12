// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{config_utils::psql, display_utils::display_success, error::EmfManagerCliError};
use emf_cmd::{CheckedCommandExt as _, OutputExt as _};
use emf_fs::mkdirp;
use emf_request_retry::{retry_future, RetryAction, RetryPolicy};
use emf_systemd::restart_unit;
use std::{collections::HashSet, fmt, path::PathBuf, time::Duration};
use structopt::StructOpt;
use tokio::fs;

fn create_policy<E: fmt::Debug>() -> impl RetryPolicy<E> {
    |k: u32, e| match k {
        0 => RetryAction::RetryNow,
        k if k < 10 => {
            let secs = 2 * k as u64;

            tracing::debug!("Waiting {} seconds for kuma to start...", secs);

            RetryAction::WaitFor(Duration::from_secs(secs))
        }
        _ => RetryAction::ReturnError(e),
    }
}

async fn wait_for_kuma() -> Result<(), EmfManagerCliError> {
    let policy = create_policy::<EmfManagerCliError>();

    retry_future(
        |_| async {
            reqwest::get("http://127.0.0.1:5681")
                .await?
                .error_for_status()?;

            Ok(())
        },
        policy,
    )
    .await?;

    Ok(())
}

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum Command {
    ///  Create the kuma control plane database
    #[structopt(name = "create-db", setting = structopt::clap::AppSettings::ColoredHelp)]
    CreateDb(CreateDb),
    /// Start requisite services
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Start,
    /// Generate TLS certificate used by the control plane server
    #[structopt(name = "generate-certs", setting = structopt::clap::AppSettings::ColoredHelp)]
    GenerateCerts(GenerateCerts),
    /// Create dataplane tokens and apply default service policies
    #[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
    Setup(Setup),
}

#[derive(Debug, Default, StructOpt)]
pub struct CreateDb {
    /// Postgres database to use for kuma info
    #[structopt(
        short,
        long,
        default_value = "kuma",
        env = "KUMA_STORE_POSTGRES_DB_NAME"
    )]
    db: String,

    /// Postgres user to access database
    #[structopt(short, long, default_value = "emf", env = "KUMA_STORE_POSTGRES_USER")]
    user: String,
}

#[derive(Debug, Default, StructOpt)]
pub struct GenerateCerts {
    #[structopt(short = "k", long = "key-file", env = "KUMA_GENERAL_TLS_KEY_FILE")]
    key_file: PathBuf,
    #[structopt(short = "c", long = "cert-file", env = "KUMA_GENERAL_TLS_CERT_FILE")]
    cert_file: PathBuf,
}

#[derive(Debug, Default, StructOpt)]
pub struct Setup {
    /// Base config dir
    #[structopt(short, long, default_value = "/etc/emf", env = "KUMA_BASE_DIR")]
    dir: PathBuf,
}

fn kumactl() -> emf_cmd::Command {
    emf_cmd::Command::new("kumactl")
}

pub async fn cli(command: Command) -> Result<(), EmfManagerCliError> {
    match command {
        Command::CreateDb(CreateDb { db, user }) => {
            let dbs: HashSet<String> = psql("SELECT datname FROM pg_database")
                .await?
                .lines()
                .map(|x| x.to_string())
                .collect();
            if !dbs.contains(&db) {
                psql(&format!("CREATE DATABASE {} OWNER {}", db, user)).await?;
            }
        }
        Command::GenerateCerts(GenerateCerts {
            key_file,
            cert_file,
        }) => {
            if emf_fs::file_exists(&key_file).await && emf_fs::file_exists(&cert_file).await {
                println!("Control plane certs exist, skipping");

                return Ok(());
            }

            let key_dir = match key_file.parent() {
                Some(x) => x,
                None => {
                    return Err(EmfManagerCliError::ConfigError(
                        "Cannot create key under root directory".to_string(),
                    ))
                }
            };

            let cert_dir = match cert_file.parent() {
                Some(x) => x,
                None => {
                    return Err(EmfManagerCliError::ConfigError(
                        "Cannot create cert under root directory".to_string(),
                    ))
                }
            };

            println!("Generating control plane certs...");

            if !emf_fs::dir_exists(&key_dir).await {
                mkdirp(&key_dir).await?;
            }

            if !emf_fs::dir_exists(&cert_dir).await {
                mkdirp(&cert_dir).await?;
            }

            let fqdn = emf_cmd::Command::new("hostname")
                .arg("-f")
                .checked_output()
                .await?;
            let fqdn = fqdn.try_stdout_str()?.trim();

            kumactl()
                .arg("generate")
                .arg("tls-certificate")
                .arg("--type")
                .arg("server")
                .arg("--cp-hostname")
                .arg(fqdn)
                .arg("--key-file")
                .arg(&key_file)
                .arg("--cert-file")
                .arg(&cert_file)
                .checked_output()
                .await?;

            display_success(format!(
                "Successfully generated control plane certs for {}",
                fqdn
            ));
        }
        Command::Start => restart_unit("kuma.service".to_string()).await?,
        Command::Setup(Setup { dir }) => {
            println!("Applying kuma policies...");

            wait_for_kuma().await?;

            let tokendir = dir.join("tokens");
            let policydir = dir.join("policies");

            mkdirp(&tokendir).await?;

            let out = kumactl()
                .args(vec!["generate", "dataplane-token", "--mesh", "default"])
                .checked_output()
                .await?;
            fs::write(tokendir.join("dataplane-token"), out.stdout).await?;

            kumactl()
                .args(vec![
                    "apply",
                    "-f",
                    policydir.join("mtls.yml").to_str().unwrap(),
                ])
                .checked_output()
                .await?;

            kumactl()
                .args(vec![
                    "apply",
                    "-f",
                    policydir.join("traffic.yml").to_str().unwrap(),
                ])
                .checked_output()
                .await?;

            display_success("Successfully applied kuma policies");
        }
    }
    Ok(())
}
