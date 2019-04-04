// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::ToBytes;
use std::net::SocketAddr;

use failure::Error;
use futures::future::{self, Either, Future};
use iml_manager_env;
use lapin_futures::{
    channel::{
        BasicConsumeOptions, BasicProperties, BasicPublishOptions, Channel, ExchangeDeclareOptions,
        QueueBindOptions, QueueDeclareOptions, QueuePurgeOptions,
    },
    client::{Client, ConnectionOptions, Heartbeat},
    consumer::Consumer,
    error::Error as LapinError,
    queue::Queue,
    types::FieldTable,
};
use tokio::net::TcpStream;

pub type TcpClient = Client<TcpStream>;
pub type TcpChannel = Channel<TcpStream>;
pub type TcpStreamConsumer = Consumer<TcpStream>;

pub trait TcpClientFuture: Future<Item = TcpClient, Error = failure::Error> {}
impl<T: Future<Item = TcpClient, Error = failure::Error>> TcpClientFuture for T {}

pub trait TcpChannelFuture: Future<Item = TcpChannel, Error = failure::Error> {}
impl<T: Future<Item = TcpChannel, Error = failure::Error>> TcpChannelFuture for T {}

pub trait TcpStreamConsumerFuture:
    Future<Item = TcpStreamConsumer, Error = failure::Error>
{
}
impl<T: Future<Item = TcpStreamConsumer, Error = failure::Error>> TcpStreamConsumerFuture for T {}

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
) -> impl Future<Item = (TcpChannel, Queue), Error = failure::Error> + 'static {
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

pub fn basic_publish<T: ToBytes + std::fmt::Debug>(
    exchange: &str,
    routing_key: &str,
    channel: TcpChannel,
    req: T,
) -> impl TcpChannelFuture {
    log::info!("publishing Request: {:?}", req);

    match req.to_bytes() {
        Ok(bytes) => Either::A(
            channel
                .basic_publish(
                    exchange,
                    routing_key,
                    bytes,
                    BasicPublishOptions::default(),
                    BasicProperties::default()
                        .with_content_type("application/json".into())
                        .with_content_encoding("utf-8".into())
                        .with_priority(0),
                )
                .map(|confirmation| log::info!("publish got confirmation: {:?}", confirmation))
                .map(|_| channel)
                .from_err(),
        ),
        Err(e) => Either::B(future::err(e.into())),
    }
}

pub fn declare_queue<'a>(
    name: String,
    c: TcpChannel,
) -> impl Future<Item = (TcpChannel, Queue), Error = failure::Error> + 'a {
    queue_declare(
        c,
        &name,
        Some(QueueDeclareOptions {
            durable: false,
            ..Default::default()
        }),
    )
}

pub fn connect_to_rabbit() -> impl Future<Item = TcpClient, Error = Error> {
    connect(
        &iml_manager_env::get_addr(),
        ConnectionOptions {
            username: iml_manager_env::get_user(),
            password: iml_manager_env::get_password(),
            vhost: iml_manager_env::get_vhost(),
            ..ConnectionOptions::default()
        },
    )
    .map(|(client, heartbeat)| {
        // The heartbeat future should be run in a dedicated thread so that nothing can prevent it from
        // dispatching events on time.
        // If we ran it as part of the "main" chain of futures, we might end up not sending
        // some heartbeats if we don't poll often enough (because of some blocking task or such).
        tokio::spawn(heartbeat.map_err(|_| ()));

        client
    })
}

pub fn connect_to_queue<'a>(
    name: String,
    client: TcpClient,
) -> impl Future<Item = (TcpChannel, Queue), Error = failure::Error> + 'a {
    create_channel(client).and_then(move |ch| declare_queue(name, ch))
}
