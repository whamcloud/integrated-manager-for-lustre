// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_timer::{
    command::spawn_command,
    config::{delete_config, get_config, service_file, timer_file, unit_name, write_configs},
    error::{customize_error, TimerError},
};
use tokio::process::Command;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};
use warp::{self, http::StatusCode, Filter};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    // Match a config route
    let config_route = warp::put()
        .and(warp::path("config"))
        .and(warp::body::content_length_limit(1024 * 16))
        .and(warp::body::json())
        .map(get_config)
        .and_then(write_configs)
        .and_then(move |config_id: String| {
            async move {
                spawn_command(
                    Command::new("systemctl").arg("daemon-reload"),
                    config_id,
                    TimerError::DaemonReloadFailed,
                )
                .await
            }
        })
        .and_then(move |config_id: String| {
            async move {
                let timer_path = format!("{}.timer", unit_name(config_id.as_str()));
                spawn_command(
                    Command::new("systemctl")
                        .arg("enable")
                        .arg("--now")
                        .arg(timer_path),
                    config_id,
                    TimerError::EnableTimerError,
                )
                .await
            }
        })
        .map(|_| Ok(StatusCode::CREATED));

    let unconfigure_route = warp::delete()
        .and(warp::path("config"))
        .and(warp::body::content_length_limit(1024 * 16))
        .and(warp::body::json())
        .and_then(move |config_id: String| {
            async move {
                let timer_path = format!("{}.timer", unit_name(config_id.as_str()));
                spawn_command(
                    Command::new("systemctl")
                        .arg("disable")
                        .arg("--now")
                        .arg(timer_path),
                    config_id,
                    TimerError::DisableTimerError,
                )
                .await
            }
        })
        .and_then(move |config_id: String| {
            async move {
                let timer_path = timer_file(config_id.as_str());
                delete_config(&timer_path, config_id).await
            }
        })
        .and_then(move |config_id: String| {
            async move {
                let timer_path = service_file(config_id.as_str());
                delete_config(&timer_path, config_id).await
            }
        })
        .and_then(move |_| {
            async move {
                spawn_command(
                    Command::new("systemctl").arg("daemon-reload"),
                    (),
                    TimerError::DaemonReloadFailed,
                )
                .await
            }
        })
        .map(|_| Ok(StatusCode::NO_CONTENT));

    let routes = config_route.or(unconfigure_route).recover(customize_error);

    warp::serve(routes)
        .run(iml_manager_env::get_timer_addr())
        .await;

    Ok(())
}
