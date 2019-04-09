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
        .from_err()
}

pub fn declare_transient_exchange(
    channel: TcpChannel,
    name: &str,
    exchange_type: &str,
) -> impl TcpChannelFuture {
    exchange_declare(
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
        .from_err()
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
        .from_err()
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
    consumer_tag: &str,
    options: Option<BasicConsumeOptions>,
) -> impl TcpStreamConsumerFuture {
    let options = match options {
        Some(o) => o,
        None => BasicConsumeOptions::default(),
    };

    channel
        .basic_consume(&queue, &consumer_tag, options, FieldTable::new())
        .from_err()
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
    exchange: impl Into<String>,
    routing_key: &str,
    channel: TcpChannel,
    req: T,
) -> impl TcpChannelFuture {
    log::info!("publishing Request: {:?}", req);

    match req.to_bytes() {
        Ok(bytes) => Either::A(
            channel
                .basic_publish(
                    &exchange.into(),
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

pub fn declare_transient_queue(
    name: String,
    c: TcpChannel,
) -> impl Future<Item = (TcpChannel, Queue), Error = failure::Error> {
    queue_declare(
        c,
        &name,
        Some(QueueDeclareOptions {
            durable: false,
            ..Default::default()
        }),
    )
}

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

pub fn connect_to_queue(
    name: String,
    client: TcpClient,
) -> impl Future<Item = (TcpChannel, Queue), Error = failure::Error> {
    create_channel(client).and_then(move |ch| declare_transient_queue(name, ch))
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
        basic_publish, connect, create_channel, declare_transient_exchange,
        declare_transient_queue, get_cloned_conns, queue_bind, TcpClientFuture,
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
            .and_then(move |ch| declare_transient_queue(queue_name.to_string(), ch))
            .and_then(move |(c, _)| queue_bind(c, exchange_name, queue_name))
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
                        .and_then(|ch| declare_transient_queue("fooQ".to_string(), ch))
                        .and_then(move |(c, _)| queue_bind(c, "foo", "fooQ"))
                        .and_then(|ch| basic_publish("foo", "fooQ", ch, "bar"))
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
                .and_then(|ch| declare_transient_queue("fooQ2".to_string(), ch))
                .and_then(move |(c, _)| queue_bind(c, "foo2", "fooQ2"))
                .and_then(|ch| basic_publish("foo2", "fooQ2", ch, "bar"))
                .and_then(|_| read_message("foo2", "fooQ2")),
        )?;

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"bar\"", actual);

        let (tx2, rx2) = oneshot::channel();

        tx.unbounded_send(tx2)?;

        let client = rt.block_on(rx2)?;

        let msg = rt.block_on(
            create_channel(client)
                .and_then(|ch| basic_publish("foo2", "fooQ2", ch, "baz"))
                .and_then(|_| read_message("foo2", "fooQ2")),
        )?;

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"baz\"", actual);

        Ok(())
    }
}
