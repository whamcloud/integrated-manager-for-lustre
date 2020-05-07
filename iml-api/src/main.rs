// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

mod action;
mod command;
mod error;
mod task;

use futures::{
    channel::{mpsc, oneshot},
    future, Future, StreamExt as _, TryFutureExt,
};
use iml_orm::DbPool;
use iml_rabbit::{self, create_connection_filter};
use iml_wire_types::Conf;
use warp::Filter;

type PoolSender = oneshot::Sender<DbPool>;
pub fn get_cloned_pool(
    pool: DbPool,
) -> (mpsc::UnboundedSender<PoolSender>, impl Future<Output = ()>) {
    let (tx, rx) = mpsc::unbounded();

    let fut = rx.for_each(move |sender: PoolSender| {
        let _ = sender
            .send(pool.clone())
            .map_err(|_| tracing::info!("channel recv dropped before we could hand out a pool"));

        future::ready(())
    });

    (tx, fut)
}

pub async fn create_pool_filter() -> Result<
    (
        impl Future<Output = ()>,
        impl Filter<Extract = (DbPool,), Error = warp::Rejection> + Clone,
    ),
    error::ImlApiError,
> {
    let conn = iml_orm::pool()?;

    let (tx, fut) = get_cloned_pool(conn);

    let filter = warp::any().and_then(move || {
        let (tx2, rx2) = oneshot::channel();

        tx.unbounded_send(tx2).unwrap();

        rx2.map_err(error::ImlApiError::OneshotCanceled)
            .map_err(warp::reject::custom)
    });

    Ok((fut, filter))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    iml_tracing::init();

    let addr = iml_manager_env::get_iml_api_addr();

    let conf = Conf {
        allow_anonymous_read: iml_manager_env::get_allow_anonymous_read(),
        build: iml_manager_env::get_build(),
        version: iml_manager_env::get_version(),
        is_release: iml_manager_env::get_is_release(),
        branding: iml_manager_env::get_branding().into(),
        use_stratagem: iml_manager_env::get_use_stratagem(),
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
