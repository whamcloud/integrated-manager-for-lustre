// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::net::SocketAddr;

use failure::Error;
use futures::future::Future;
use lapin_futures::{
    channel::{
        BasicConsumeOptions, BasicProperties, BasicPublishOptions, ExchangeDeclareOptions,
        QueueBindOptions, QueueDeclareOptions, QueuePurgeOptions,
    },
    client::{Client, ConnectionOptions, Heartbeat},
    consumer::Consumer,
    error::Error as LapinError,
    queue::Queue,
    types::FieldTable,
};
use tokio::net::TcpStream;

use crate::{TcpChannel, TcpChannelFuture, TcpClient};

/// Connects over TCP to an AMQP server
///
/// # Arguments
///
/// * `addr` - A `SocketAddr` to connect to
/// * `opts` - `ConnectionOptions` to configure the connection
pub fn connect(
    addr: &SocketAddr,
    opts: ConnectionOptions,
) -> impl Future<
    Item = (
        TcpClient,
        Heartbeat<impl Future<Item = (), Error = LapinError> + Send + 'static>,
    ),
    Error = Error,
> {
    TcpStream::connect(addr)
        .map_err(Error::from)
        .and_then(|stream| Client::connect(stream, opts).map_err(Error::from))
}

/// Creates a channel for the passed in client
///
/// # Arguments
///
/// * `client` - A `TcpClient` to create a channel on
pub fn create_channel(client: TcpClient) -> impl TcpChannelFuture {
    log::info!("creating client");

    client
        .create_channel()
        .inspect(|channel| log::info!("created channel with id: {}", channel.id))
        .map_err(failure::Error::from)
}

/// Declares an exhange if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `name` - The name of the exchange
/// * `exchange_type` - The type of the exchange
/// * `options` - An `Option<ExchangeDeclareOptions>` of additional options to pass in. If not supplied, `ExchangeDeclareOptions::default()` is used
pub fn exchange_declare(
    channel: TcpChannel,
    name: &str,
    exchange_type: &str,
    options: Option<ExchangeDeclareOptions>,
) -> impl TcpChannelFuture {
    log::info!("declaring exchange {}", name);

    let options = match options {
        Some(o) => o,
        None => ExchangeDeclareOptions::default(),
    };

    channel
        .exchange_declare(name, exchange_type, options, FieldTable::new())
        .map(|_| channel)
        .map_err(failure::Error::from)
}

/// Declares a queue if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `name` - The name of the queue
/// * `options` - An `Option<QueueDeclareOptions>` of additional options to pass in. If not supplied, `QueueDeclareOptions::default()` is used
pub fn queue_declare(
    channel: TcpChannel,
    name: &str,
    options: Option<QueueDeclareOptions>,
) -> impl Future<Item = (TcpChannel, Queue), Error = failure::Error> {
    log::info!("declaring queue {}", name);

    let options = match options {
        Some(o) => o,
        None => QueueDeclareOptions::default(),
    };

    channel
        .queue_declare(name, options, FieldTable::new())
        .map(|queue| (channel, queue))
        .map_err(failure::Error::from)
}

/// Binds a queue to an exchange
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `exchange_name` - The name of the exchange
/// * `queue_name` - The name of the queue
pub fn queue_bind(
    channel: TcpChannel,
    exchange_name: &str,
    queue_name: &str,
) -> impl TcpChannelFuture {
    channel
        .queue_bind(
            queue_name,
            exchange_name,
            queue_name,
            QueueBindOptions::default(),
            FieldTable::new(),
        )
        .map(|_| channel)
        .map_err(failure::Error::from)
}

/// Purges contents of a queue
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `queue_name` - The name of the queue
pub fn queue_purge(channel: TcpChannel, queue_name: &str) -> impl TcpChannelFuture {
    channel
        .queue_purge(queue_name, QueuePurgeOptions::default())
        .map(|_| channel)
        .map_err(failure::Error::from)
}

/// Starts consuming from a queue
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `queue` - The queue to use
/// * `consumer_tag` - The tag for the consumer
/// * `options` - An `Option<BasicConsumeOptions>` of additional options to pass in. If not supplied, `BasicConsumeOptions::default()` is used
pub fn basic_consume(
    channel: TcpChannel,
    queue: Queue,
    consumer_tag: &str,
    options: Option<BasicConsumeOptions>,
) -> impl Future<Item = Consumer<tokio::net::TcpStream>, Error = failure::Error> {
    let options = match options {
        Some(o) => o,
        None => BasicConsumeOptions::default(),
    };

    channel
        .basic_consume(&queue, &consumer_tag, options, FieldTable::new())
        .map_err(failure::Error::from)
}

pub fn declare(channel: TcpChannel) -> impl TcpChannelFuture {
    let exchange_name = "rpc";
    let queue_name = "JobSchedulerRpc.requests";

    exchange_declare(
        channel,
        exchange_name,
        "topic",
        Some(ExchangeDeclareOptions {
            durable: false,
            ..Default::default()
        }),
    )
    .and_then(move |c| queue_declare(c, queue_name, None))
    .and_then(move |(c, _)| queue_bind(c, exchange_name, queue_name))
}

pub fn basic_publish<T: Into<Vec<u8>> + std::fmt::Debug>(
    channel: TcpChannel,
    req: T,
) -> impl TcpChannelFuture {
    log::info!("publishing Request: {:?}", req);

    channel
        .basic_publish(
            "rpc",
            "JobSchedulerRpc.requests",
            req.into(),
            BasicPublishOptions::default(),
            BasicProperties::default()
                .with_content_type("application/json".into())
                .with_content_encoding("utf-8".into())
                .with_priority(0),
        )
        .map(|confirmation| log::info!("publish got confirmation: {:?}", confirmation))
        .map(|_| channel)
        .map_err(failure::Error::from)
}
