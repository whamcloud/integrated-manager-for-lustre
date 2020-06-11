// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod action;
mod command;
mod error;
mod task;

use iml_orm::create_pool_filter;
use iml_rabbit::{self, create_connection_filter};
use iml_wire_types::Conf;
use warp::Filter;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let addr = iml_manager_env::get_iml_api_addr();

    let conf = Conf {
        allow_anonymous_read: iml_manager_env::get_allow_anonymous_read(),
        build: iml_manager_env::get_build(),
        version: iml_manager_env::get_version(),
        exascaler_version: iml_manager_env::get_exascaler_version(),
        is_release: iml_manager_env::get_is_release(),
        branding: iml_manager_env::get_branding().into(),
        use_stratagem: iml_manager_env::get_use_stratagem(),
        monitor_sfa: iml_manager_env::get_sfa_endpoints().is_some(),
    };

    let (cli_fut, client_filter) = create_connection_filter().await?;
    let (pool_fut, pool_filter) = create_pool_filter().await?;

    tokio::spawn(cli_fut);
    tokio::spawn(pool_fut);

    let routes = warp::path("conf")
        .map(move || warp::reply::json(&conf))
        .or(action::endpoint(client_filter.clone()))
        .or(task::endpoint(client_filter, pool_filter));

    tracing::info!("Starting on {:?}", addr);

    let log = warp::log::custom(|info| {
        tracing::debug!(
            "{:?} \"{} {} {:?}\" {} \"{:?}\" \"{:?}\" {:?}",
            info.remote_addr(),
            info.method(),
            info.path(),
            info.version(),
            info.status().as_u16(),
            info.referer(),
            info.user_agent(),
            info.elapsed(),
        );
    });

    warp::serve(
        routes
            .or_else(|e| async {
                tracing::error!("{:?}", e);

                Err(e)
            })
            .with(log),
    )
    .run(addr)
    .await;

    Ok(())
}
