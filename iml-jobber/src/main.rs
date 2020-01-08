// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::process::Command;
use std::{
    fs::File,
    io::prelude::*,
    str::{from_utf8, Utf8Error},
};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};
use warp::{self, Buf, Filter};

static CONFIG_FILE: &str = "/home/jobberuser/.jobber";

fn get_config(mut full_body: warp::body::FullBody) -> Result<String, Utf8Error> {
    // Build the config string from the buffer.
    let mut remaining = full_body.remaining();
    let mut data: String = String::new();
    while remaining != 0 {
        let current_bytes = full_body.bytes();
        data.push_str(from_utf8(&current_bytes)?);
        let cnt = current_bytes.len();
        full_body.advance(cnt);
        remaining -= cnt;
    }

    Ok(data)
}

fn write_config_to_file(buf: &[u8], file: &str) -> std::io::Result<()> {
    let mut file = File::create(file)?;
    file.write_all(buf)?;
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
        .and(warp::body::concat())
        .map(get_config)
        .map(|data: Result<String, Utf8Error>| match data {
            Ok(config) => {
                if let Ok(()) = write_config_to_file(config.as_bytes(), CONFIG_FILE) {
                    tracing::debug!("Successfully wrote jobber config file at {}.", CONFIG_FILE);
                    warp::http::StatusCode::OK
                } else {
                    tracing::error!("Couldn't write jobber config file at {}.", CONFIG_FILE);
                    warp::http::StatusCode::INTERNAL_SERVER_ERROR
                }
            }
            Err(e) => {
                tracing::error!("Error processing config data: {:?}", e);
                warp::http::StatusCode::INTERNAL_SERVER_ERROR
            }
        })
        .map(|status: warp::http::StatusCode| match status {
            warp::http::StatusCode::OK => match Command::new("jobber reload").spawn() {
                Ok(_) => {
                    tracing::debug!("Reloaded jobber daemon.");
                    warp::reply::with_status(warp::reply(), warp::http::StatusCode::OK)
                }
                Err(e) => {
                    tracing::error!("Failed to reload the jobber service: {:?}", e);
                    warp::reply::with_status(
                        warp::reply(),
                        warp::http::StatusCode::INTERNAL_SERVER_ERROR,
                    )
                }
            },
            _ => warp::reply::with_status(warp::reply(), status),
        });

    warp::serve(config_route).run(([127, 0, 0, 1], 3030)).await;
}
