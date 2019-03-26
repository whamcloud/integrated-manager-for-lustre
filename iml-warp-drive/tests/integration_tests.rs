#![type_length_limit = "2097152"]

use std::{env, net::SocketAddr};

use futures::future::Future;
use lapin_futures::{
    channel::BasicGetOptions, client::ConnectionOptions, message::BasicGetMessage,
};
use tokio::runtime::Runtime;

use iml_warp_drive::{
    rabbit::{basic_publish, connect, create_channel, declare},
    request::Request,
};

fn get_addr() -> SocketAddr {
    "127.0.0.1:5672".to_string().parse().unwrap()
}

fn read_message() -> impl Future<Item = BasicGetMessage, Error = failure::Error> {
    connect(&get_addr(), ConnectionOptions::default())
        .map(|(client, mut heartbeat)| {
            let handle = heartbeat.handle().unwrap();

            handle.stop();

            client
        })
        .and_then(create_channel)
        .and_then(declare)
        .and_then(|channel| {
            channel
                .basic_get(
                    "JobSchedulerRpc.requests",
                    BasicGetOptions {
                        no_ack: true,
                        ..Default::default()
                    },
                )
                .map_err(failure::Error::from)
        })
}

#[test]
fn test_connect() -> Result<(), failure::Error> {
    env::set_var("RUST_LOG", "debug");
    let _ = env_logger::try_init();

    let addr = "127.0.0.1:5672".to_string().parse().unwrap();

    let msg = Runtime::new().unwrap().block_on_all(
        connect(&addr, ConnectionOptions::default())
            .and_then(|(client, mut heartbeat)| {
                let handle = heartbeat.handle().unwrap();

                handle.stop();

                create_channel(client)
                    .and_then(declare)
                    .and_then(|c| basic_publish(c, Request::new("get_locks", "locks")))
            })
            .and_then(|_| read_message()),
    )?;

    let actual: Request = serde_json::from_slice(&msg.delivery.data)?;

    assert_eq!(actual.method, "get_locks");
    assert_eq!(actual.response_routing_key, "locks");

    Ok(())
}
