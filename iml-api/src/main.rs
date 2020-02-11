// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod action;
mod error;

use iml_rabbit::{self, create_client_filter};
use iml_wire_types::Conf;
use tracing_subscriber::{fmt::Subscriber, EnvFilter};
use warp::Filter;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr = iml_manager_env::get_iml_api_addr();

    let conf = Conf {
        allow_anonymous_read: iml_manager_env::get_allow_anonymous_read(),
        build: iml_manager_env::get_build(),
        version: iml_manager_env::get_version(),
        is_release: iml_manager_env::get_is_release(),
    };

    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    let (fut, client_filter) = create_client_filter().await?;

    tokio::spawn(fut);

    let routes = warp::path("conf")
        .map(move || warp::reply::json(&conf))
        .or(action::endpoint(client_filter));

    tracing::info!("Starting on {:?}", addr);

    warp::serve(routes.with(warp::log("iml-api")))
        .run(addr)
        .await;

    Ok(())
}
