// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod action;
mod command;
mod error;
pub mod graphql;
mod timer;

use iml_manager_env::get_pool_limit;
use iml_postgres::get_db_pool;
use iml_rabbit::{self, create_connection_filter};
use iml_wire_types::Conf;
use std::sync::Arc;
use warp::Filter;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 5;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    dotenv::from_path(".env").expect("Could not load cli env");
    iml_tracing::init();

    let addr = iml_manager_env::get_iml_api_addr();

    let conf = Conf {
        allow_anonymous_read: iml_manager_env::get_allow_anonymous_read(),
        build: iml_manager_env::get_build(),
        version: iml_manager_env::get_version(),
        exa_version: iml_manager_env::get_exa_version(),
        is_release: iml_manager_env::get_is_release(),
        branding: iml_manager_env::get_branding().into(),
        use_stratagem: iml_manager_env::get_use_stratagem(),
        use_snapshots: iml_manager_env::get_use_snapshots(),
        monitor_sfa: iml_manager_env::get_sfa_endpoints().is_some(),
    };

    let rabbit_pool = iml_rabbit::connect_to_rabbit(2);

    let conn_filter = create_connection_filter(rabbit_pool.clone());

    let pg_pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT)).await?;

    let schema = Arc::new(graphql::Schema::new(
        graphql::QueryRoot,
        graphql::MutationRoot,
        juniper::EmptySubscription::new(),
    ));
    let schema_filter = warp::any().map(move || Arc::clone(&schema));

    let ctx = Arc::new(graphql::Context {
        pg_pool,
        rabbit_pool,
    });
    let ctx_filter = warp::any().map(move || Arc::clone(&ctx));

    let routes = warp::path("conf")
        .map(move || warp::reply::json(&conf))
        .or(action::endpoint(conn_filter.clone()))
        .or(graphql::endpoint(schema_filter, ctx_filter));

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
