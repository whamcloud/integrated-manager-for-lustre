// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use failure::Error;
use futures::{
    future::{self, Either, Future},
    stream::Stream as _,
    sync::{mpsc, oneshot},
};
use iml_manager_env;
use iml_wire_types::ToBytes;
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
use std::net::SocketAddr;
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
        Heartbeat<impl Future<Item = (), Error = LapinError>>,
    ),
    Error = Error,
> {
    log::info!("creating client");

    TcpStream::connect(addr)
        .from_err()
        .and_then(|stream| Client::connect(stream, opts).from_err())
}

/// Creates a channel for the passed in client
///
/// # Arguments
///
/// * `client` - A `TcpClient` to create a channel on
pub fn create_channel(client: TcpClient) -> impl TcpChannelFuture {
    client
        .create_channel()
        .inspect(|channel| log::debug!("created channel with id: {}", channel.id))
        .from_err()
}

/// Closes the channel
///
/// # Arguments
///
/// * `channel` - The TcpChannel to use
pub fn close_channel(channel: TcpChannel) -> impl Future<Item = (), Error = failure::Error> {
    let id = channel.id;

    channel
        .close(200, "OK")
        .map(move |_| log::debug!("closed channel with id: {}", id))
        .from_err()
}

/// Declares an exhange if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `name` - The name of the exchange
/// * `exchange_type` - The type of the exchange
/// * `options` - An `Option<ExchangeDeclareOptions>` of additional options to pass in. If not supplied, `ExchangeDeclareOptions::default()` is used
pub fn declare_exchange(
    channel: TcpChannel,
    name: impl Into<String>,
    exchange_type: impl Into<String>,
    options: Option<ExchangeDeclareOptions>,
) -> impl TcpChannelFuture {
    let name = name.into();
    let exchange_type = exchange_type.into();
    let options = options.unwrap_or_default();

    log::info!("declaring exchange: {}, type: {}", name, exchange_type);

    channel
        .exchange_declare(&name, &exchange_type, options, FieldTable::new())
        .map(|_| channel)
        .from_err()
}

/// Declares a transient exhange if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `name` - The name of the exchange
/// * `exchange_type` - The type of the exchange
pub fn declare_transient_exchange(
    channel: TcpChannel,
    name: impl Into<String>,
    exchange_type: impl Into<String>,
) -> impl TcpChannelFuture {
    declare_exchange(
        channel,
        name,
        exchange_type,
        Some(ExchangeDeclareOptions {
            durable: false,
            ..Default::default()
        }),
    )
}

/// Declares a queue if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `name` - The name of the queue
/// * `options` - An `Option<QueueDeclareOptions>` of additional options to pass in. If not supplied, `QueueDeclareOptions::default()` is used
pub fn declare_queue(
    channel: TcpChannel,
    name: impl Into<String>,
    options: Option<QueueDeclareOptions>,
) -> impl Future<Item = (TcpChannel, Queue), Error = failure::Error> {
    let name = name.into();
    let options = options.unwrap_or_default();

    log::info!("declaring queue {}", name);

    channel
        .queue_declare(&name, options, FieldTable::new())
        .map(|queue| (channel, queue))
        .from_err()
}

/// Declares a transient queue if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `name` - The name of the queue
pub fn declare_transient_queue(
    channel: TcpChannel,
    name: impl Into<String>,
) -> impl Future<Item = (TcpChannel, Queue), Error = failure::Error> {
    declare_queue(
        channel,
        name,
        Some(QueueDeclareOptions {
            durable: false,
            ..Default::default()
        }),
    )
}

/// Binds a queue to an exchange
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `exchange_name` - The name of the exchange
/// * `queue_name` - The name of the queue
/// * `routing_key` - The routing key
pub fn bind_queue(
    channel: TcpChannel,
    exchange_name: impl Into<String>,
    queue_name: impl Into<String>,
    routing_key: impl Into<String>,
) -> impl TcpChannelFuture {
    channel
        .queue_bind(
            &queue_name.into(),
            &exchange_name.into(),
            &routing_key.into(),
            QueueBindOptions::default(),
            FieldTable::new(),
        )
        .map(|_| channel)
        .from_err()
}

pub fn connect_to_queue(
    name: impl Into<String>,
    client: TcpClient,
) -> impl Future<Item = (TcpChannel, Queue), Error = failure::Error> {
    create_channel(client).and_then(move |ch| declare_transient_queue(ch, name))
}

/// Purges contents of a queue
///
/// # Arguments
///
/// * `channel` - The `TcpChannel` to use
/// * `queue_name` - The name of the queue
pub fn purge_queue(channel: TcpChannel, queue_name: impl Into<String>) -> impl TcpChannelFuture {
    channel
        .queue_purge(&queue_name.into(), QueuePurgeOptions::default())
        .map(|_| channel)
        .from_err()
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
    consumer_tag: impl Into<String>,
    options: Option<BasicConsumeOptions>,
) -> impl TcpStreamConsumerFuture {
    let options = options.unwrap_or_default();

    channel
        .basic_consume(&queue, &consumer_tag.into(), options, FieldTable::new())
        .from_err()
}

/// Publish a message to a given exchange
///
/// # Arguments
///
/// * `exhange` - The exchange to publish to
/// * `routing_key` - Where to route the message
/// * `channel` - The channel to use for publishing
/// * `msg` - The message to publish. Must implement `ToBytes + std::fmt::Debug`
pub fn basic_publish<T: ToBytes + std::fmt::Debug>(
    channel: TcpChannel,
    exchange: impl Into<String>,
    routing_key: impl Into<String>,
    msg: T,
) -> impl TcpChannelFuture {
    log::debug!("publishing Message: {:?}", msg);

    match msg.to_bytes() {
        Ok(bytes) => Either::A(
            channel
                .basic_publish(
                    &exchange.into(),
                    &routing_key.into(),
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

/// Sends a JSON encoded message to the given exchange / queue
pub fn send_message<T: ToBytes + std::fmt::Debug>(
    client: TcpClient,
    exchange_name: impl Into<String>,
    queue_name: impl Into<String>,
    msg: T,
) -> impl Future<Item = (), Error = failure::Error> {
    create_channel(client.clone())
        .and_then(|ch| declare_transient_queue(ch, queue_name))
        .and_then(move |(c, q)| basic_publish(c, exchange_name, q.name(), msg))
        .and_then(close_channel)
}

/// Connect to the rabbitmq instance running on the IML manager
///
/// This fn is useful for production code as it reads in env vars
/// to make a connection.
///
pub fn connect_to_rabbit() -> impl TcpClientFuture {
    connect(
        &iml_manager_env::get_addr(),
        ConnectionOptions {
            username: iml_manager_env::get_user(),
            password: iml_manager_env::get_password(),
            vhost: iml_manager_env::get_vhost(),
            heartbeat: 0, // Turn off heartbeat due to https://github.com/sozu-proxy/lapin/issues/152
            ..ConnectionOptions::default()
        },
    )
    .map(|(client, mut heartbeat)| {
        let handle = heartbeat.handle().unwrap();

        handle.stop();

        client
    })
}

type ClientSender = oneshot::Sender<TcpClient>;

/// Given a `TcpClientFuture`, this fn will
/// return a `(UnboundedSender, Future)` pair.
///
/// The future can be spawned on a runtime,
/// and the `UnboundedSender` can be passed a
/// `oneshot::Sender` to get a cloned connection.
///
/// This is useful for multiplexing channels over a
/// single connection.
pub fn get_cloned_conns(
    conn_fut: impl TcpClientFuture,
) -> (
    mpsc::UnboundedSender<ClientSender>,
    impl Future<Item = (), Error = ()>,
) {
    let (tx, rx) = mpsc::unbounded();

    let fut = conn_fut
        .map_err(|e| log::error!("There was an error connecting to rabbit: {:?}", e))
        .and_then(|conn| {
            rx.for_each(move |sender: ClientSender| {
                sender.send(conn.clone()).map_err(|_| {
                    log::info!("channel recv dropped before we could hand out a connection")
                })
            })
        });

    (tx, fut)
}

#[cfg(test)]
mod tests {
    use super::{
        basic_publish, bind_queue, connect, create_channel, declare_transient_exchange,
        declare_transient_queue, get_cloned_conns, TcpClientFuture,
    };
    use futures::{future::Future, sync::oneshot};
    use lapin_futures::{
        channel::BasicGetOptions, client::ConnectionOptions, message::BasicGetMessage,
    };
    use tokio::runtime::Runtime;

    fn read_message(
        exchange_name: &'static str,
        queue_name: &'static str,
    ) -> impl Future<Item = BasicGetMessage, Error = failure::Error> {
        create_test_connection()
            .and_then(create_channel)
            .and_then(move |ch| declare_transient_exchange(ch, exchange_name, "direct"))
            .and_then(move |ch| declare_transient_queue(ch, queue_name.to_string()))
            .and_then(move |(c, _)| bind_queue(c, exchange_name, queue_name, ""))
            .and_then(move |channel| {
                channel
                    .basic_get(
                        queue_name,
                        BasicGetOptions {
                            no_ack: true,
                            ..Default::default()
                        },
                    )
                    .map_err(failure::Error::from)
            })
    }

    fn create_test_connection() -> impl TcpClientFuture {
        let addr = "127.0.0.1:5672".to_string().parse().unwrap();

        connect(&addr, ConnectionOptions::default()).map(|(client, mut heartbeat)| {
            let handle = heartbeat.handle().unwrap();

            handle.stop();

            client
        })
    }

    #[test]
    fn test_connect() -> Result<(), failure::Error> {
        let msg = Runtime::new()?.block_on_all(
            create_test_connection()
                .and_then(|client| {
                    create_channel(client)
                        .and_then(|ch| declare_transient_exchange(ch, "foo", "direct"))
                        .and_then(|ch| declare_transient_queue(ch, "fooQ"))
                        .and_then(move |(c, _)| bind_queue(c, "foo", "fooQ", "fooQ"))
                        .and_then(|ch| basic_publish(ch, "foo", "fooQ", "bar"))
                })
                .and_then(|_| read_message("foo", "fooQ")),
        )?;

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"bar\"", actual);

        Ok(())
    }

    #[test]
    fn test_get_cloned_conns() -> Result<(), failure::Error> {
        let mut rt = Runtime::new()?;

        let (tx, fut) = get_cloned_conns(create_test_connection());

        rt.spawn(fut);

        let (tx2, rx2) = oneshot::channel();

        tx.unbounded_send(tx2)?;

        let client = rt.block_on(rx2)?;

        let msg = rt.block_on(
            create_channel(client)
                .and_then(|ch| declare_transient_exchange(ch, "foo2", "direct"))
                .and_then(|ch| declare_transient_queue(ch, "fooQ2"))
                .and_then(move |(c, _)| bind_queue(c, "foo2", "fooQ2", "fooQ2"))
                .and_then(|ch| basic_publish(ch, "foo2", "fooQ2", "bar"))
                .and_then(|_| read_message("foo2", "fooQ2")),
        )?;

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"bar\"", actual);

        let (tx2, rx2) = oneshot::channel();

        tx.unbounded_send(tx2)?;

        let client = rt.block_on(rx2)?;

        let msg = rt.block_on(
            create_channel(client)
                .and_then(|ch| basic_publish(ch, "foo2", "fooQ2", "baz"))
                .and_then(|_| read_message("foo2", "fooQ2")),
        )?;

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"baz\"", actual);

        Ok(())
    }
}
