// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod action;
mod command;
mod error;
mod graphql;
mod task;

use iml_manager_env::get_pool_limit;
use iml_postgres::get_db_pool;
use iml_rabbit::{self, create_connection_filter};
use iml_wire_types::Conf;
use iml_postgres::sqlx;
use std::sync::Arc;
use warp::Filter;

// Default pool limit if not overridden by POOL_LIMIT
const DEFAULT_POOL_LIMIT: u32 = 5;

async fn dbg_main() -> Result<(), Box<dyn std::error::Error>> {
    let conf = Conf {
        allow_anonymous_read: true,
        build: "Not Loaded".to_string(),
        version: "0".to_string(),
        exa_version: None,
        is_release: false,
        branding: Default::default(),
        use_stratagem: false,
        monitor_sfa: false,
    };
    let pg_pool = sqlx::postgres::PgPoolOptions::new()
        .max_connections(1)
        .connect("postgres://chroma@tiv1:8432/chroma")
        .await?;

    let num_rows = sqlx::query!("SELECT COUNT(*) FROM chroma_core_command")
        .fetch_one(&pg_pool)
        .await?
        .count
        .expect("Something impossible, count should not return None");

    println!("{:?}", num_rows);
    Ok(())

    // let pg_pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT)).await?;

}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    return dbg_main().await;

    let addr = iml_manager_env::get_iml_api_addr();

    let conf = Conf {
        allow_anonymous_read: iml_manager_env::get_allow_anonymous_read(),
        build: iml_manager_env::get_build(),
        version: iml_manager_env::get_version(),
        exa_version: iml_manager_env::get_exa_version(),
        is_release: iml_manager_env::get_is_release(),
        branding: iml_manager_env::get_branding().into(),
        use_stratagem: iml_manager_env::get_use_stratagem(),
        monitor_sfa: iml_manager_env::get_sfa_endpoints().is_some(),
    };

    let rabbit_pool = iml_rabbit::connect_to_rabbit(2);
    let rabbit_pool_2 = rabbit_pool.clone();

    let conn_filter = create_connection_filter(rabbit_pool);

    let pg_pool = get_db_pool(get_pool_limit().unwrap_or(DEFAULT_POOL_LIMIT)).await?;
    let pg_pool_2 = pg_pool.clone();
    let db_pool_filter = warp::any().map(move || pg_pool.clone());

    let schema = Arc::new(graphql::Schema::new(
        graphql::QueryRoot,
        graphql::MutationRoot,
        juniper::EmptySubscription::new(),
    ));
    let schema_filter = warp::any().map(move || Arc::clone(&schema));

    let ctx = Arc::new(graphql::Context {
        pg_pool: pg_pool_2,
        rabbit_pool: rabbit_pool_2,
    });
    let ctx_filter = warp::any().map(move || Arc::clone(&ctx));

    let routes = warp::path("conf")
        .map(move || warp::reply::json(&conf))
        .or(action::endpoint(conn_filter.clone()))
        .or(task::endpoint(conn_filter, db_pool_filter))
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
