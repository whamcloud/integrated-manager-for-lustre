// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use serde::{Deserialize, Serialize};
use std::process::Command;
use std::{fs::File, io::prelude::*};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};
use warp::{self, Filter};

#[derive(Deserialize, Serialize)]
struct ConfigDetails {
    interval: u64,
    config_id: String,
    filesystem_id: String,
    iml_cmd: String,
}

struct ConfigFile {
    name: String,
    content: String,
}

struct ConfigFiles {
    timer_file: ConfigFile,
    service_file: ConfigFile,
}

fn unit_name(fid: String) -> String {
    format!("iml-stratagem-{}", fid)
}

fn timer_file(fid: String) -> String {
    format!("/etc/systemd/system/{}.timer", unit_name(fid))
}

fn service_file(fid: String) -> String {
    format!("/etc/systemd/system/{}.service", unit_name(fid))
}

fn get_config(config: ConfigDetails) -> (String, ConfigFiles) {
    // Create timer file
    let timer_config = format!(
        r#"
# This file is part of IML
# This file will be overwritten automatically

[Unit]
Description=Start Stratagem run on {}

[Timer]
OnActiveSec={}
OnUnitActiveSec={}
AccuracySec=1us
"#,
        config.filesystem_id, config.interval, config.interval
    );

    let service_config = format!(
        r#"
# This file is part of IML
# This file will be overwritten automatically

[Unit]
Description=Start Stratagem run on {}

[Service]
Type=oneshot
ExecStart={}
"#,
        config.filesystem_id, config.iml_cmd
    );

    (
        config.config_id.clone(),
        ConfigFiles {
            timer_file: ConfigFile {
                name: timer_file(config.config_id.clone()),
                content: timer_config,
            },
            service_file: ConfigFile {
                name: service_file(config.config_id.clone()),
                content: service_config,
            },
        },
    )
}

fn write_config_to_file(buf: &[u8], file: &str) -> std::io::Result<()> {
    let mut file = File::create(file)?;
    file.write_all(buf)?;
    Ok(())
}

fn write_config_files(configs: ConfigFiles) -> std::io::Result<()> {
    write_config_to_file(
        configs.timer_file.content.as_bytes(),
        &configs.timer_file.name,
    )?;

    write_config_to_file(
        configs.service_file.content.as_bytes(),
        &configs.service_file.name,
    )?;

    Ok(())
}

#[tokio::main]
async fn main() {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    // Match any request and return hello world!
    let config_route = warp::put()
        .and(warp::path("config"))
        .and(warp::body::content_length_limit(1024 * 16))
        .and(warp::body::json())
        .map(get_config)
        .map(|(config_id, configs)| {
            (
                config_id,
                match write_config_files(configs) {
                    Ok(_) => warp::http::StatusCode::OK,
                    Err(_) => {
                        tracing::error!("Failed to write config files.");
                        warp::http::StatusCode::INTERNAL_SERVER_ERROR
                    }
                },
            )
        })
        .map(|(config_id, status)| match status {
            warp::http::StatusCode::OK => {
                tracing::debug!("loading the timer.");
                let reload_result = Command::new("systemctl")
                    .arg("daemon-reload")
                    .spawn()
                    .and_then(|_| {
                        Command::new("systemctl")
                            .arg("enable")
                            .arg("--now")
                            .arg(format!("{}.timer", unit_name(config_id)))
                            .spawn()
                    });

                match reload_result {
                    Ok(_) => warp::reply::with_status(warp::reply(), warp::http::StatusCode::OK),
                    Err(e) => {
                        tracing::error!("Failed to load the timer: {:?}", e);
                        warp::reply::with_status(
                            warp::reply(),
                            warp::http::StatusCode::INTERNAL_SERVER_ERROR,
                        )
                    }
                }
            }
            _ => warp::reply::with_status(warp::reply(), status),
        });

    warp::serve(config_route)
        .run(iml_manager_env::get_jobber_addr())
        .await;
}
