// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{
    channel::{mpsc, oneshot},
    compat::{Future01CompatExt, Stream01CompatExt},
    future::{self, Future},
    stream::{Stream, StreamExt},
};
use iml_manager_env;
use iml_wire_types::ToBytes;
pub use lapin_futures::{
    message,
    options::{
        BasicConsumeOptions, BasicPublishOptions, ExchangeDeclareOptions, QueueBindOptions,
        QueueDeclareOptions, QueuePurgeOptions,
    },
    types::{AMQPValue, FieldTable},
    BasicProperties, Channel, Client, ConnectionProperties, Consumer, Error as LapinError,
    ExchangeKind, Queue,
};

#[derive(Debug)]
pub enum ImlRabbitError {
    LapinError(LapinError),
    SerdeJsonError(serde_json::error::Error),
    Utf8Error(std::str::Utf8Error),
}

impl std::fmt::Display for ImlRabbitError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlRabbitError::LapinError(ref err) => write!(f, "{}", err),
            ImlRabbitError::SerdeJsonError(ref err) => write!(f, "{}", err),
            ImlRabbitError::Utf8Error(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlRabbitError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlRabbitError::LapinError(ref err) => Some(err),
            ImlRabbitError::SerdeJsonError(ref err) => Some(err),
            ImlRabbitError::Utf8Error(ref err) => Some(err),
        }
    }
}

impl From<LapinError> for ImlRabbitError {
    fn from(err: LapinError) -> Self {
        ImlRabbitError::LapinError(err)
    }
}

impl From<serde_json::error::Error> for ImlRabbitError {
    fn from(err: serde_json::error::Error) -> Self {
        ImlRabbitError::SerdeJsonError(err)
    }
}

impl From<std::str::Utf8Error> for ImlRabbitError {
    fn from(err: std::str::Utf8Error) -> Self {
        ImlRabbitError::Utf8Error(err)
    }
}

/// Connects to an AMQP server
///
/// # Arguments
///
/// * `addr` - An address to connect to
/// * `opts` - `ConnectionProperties` to configure the connection
pub async fn connect(addr: &str, options: ConnectionProperties) -> Result<Client, ImlRabbitError> {
    Client::connect(addr, options)
        .compat()
        .await
        .map_err(ImlRabbitError::from)
}

pub trait ChannelFuture: Future<Output = Result<lapin_futures::Channel, LapinError>> {}
impl<T: Future<Output = Result<lapin_futures::Channel, LapinError>>> ChannelFuture for T {}

/// Creates a channel for the passed in client
///
/// # Arguments
///
/// * `client` - A `Client` to create a channel on
pub async fn create_channel(client: Client) -> Result<lapin_futures::Channel, ImlRabbitError> {
    let chan = client.create_channel().compat().await?;

    tracing::debug!("created channel with id: {}", chan.id());

    Ok(chan)
}

/// Closes the channel
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
pub async fn close_channel(channel: Channel) -> Result<(), ImlRabbitError> {
    let id = channel.id();

    channel.close(200, "OK").compat().await?;

    tracing::debug!("closed channel with id: {}", id);

    Ok(())
}

/// Declares an exhange if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `name` - The name of the exchange
/// * `exchange_kind` - The type of the exchange
/// * `options` - An `Option<ExchangeDeclareOptions>` of additional options to pass in. If not supplied, `ExchangeDeclareOptions::default()` is used
pub async fn declare_exchange(
    channel: lapin_futures::Channel,
    name: impl Into<String>,
    exchange_kind: ExchangeKind,
    options: Option<ExchangeDeclareOptions>,
) -> Result<lapin_futures::Channel, ImlRabbitError> {
    let name = name.into();
    let options = options.unwrap_or_default();

    tracing::info!("declaring exchange: {}, type: {:?}", name, exchange_kind);

    channel
        .exchange_declare(&name, exchange_kind, options, FieldTable::default())
        .compat()
        .await?;

    Ok(channel)
}

/// Declares a transient exhange if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `name` - The name of the exchange
/// * `exchange_kind` - The type of the exchange
pub async fn declare_transient_exchange(
    channel: lapin_futures::Channel,
    name: impl Into<String>,
    exchange_kind: ExchangeKind,
) -> Result<lapin_futures::Channel, ImlRabbitError> {
    declare_exchange(
        channel,
        name,
        exchange_kind,
        Some(ExchangeDeclareOptions {
            durable: false,
            ..ExchangeDeclareOptions::default()
        }),
    )
    .await
}

/// Declares a queue if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `name` - The name of the queue
/// * `options` - An `Option<QueueDeclareOptions>` of additional options to pass in. If not supplied, `QueueDeclareOptions::default()` is used
pub async fn declare_queue(
    channel: Channel,
    name: impl Into<String>,
    options: Option<QueueDeclareOptions>,
    field_table: Option<FieldTable>,
) -> Result<(Channel, Queue), ImlRabbitError> {
    let name = name.into();
    let options = options.unwrap_or_default();
    let field_table = field_table.unwrap_or_default();

    tracing::debug!("declaring queue {}", name);

    let queue = channel
        .queue_declare(&name, options, field_table)
        .compat()
        .await?;

    Ok((channel, queue))
}

/// Declares a transient queue if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `name` - The name of the queue
pub async fn declare_transient_queue(
    channel: Channel,
    name: impl Into<String>,
) -> Result<(Channel, Queue), ImlRabbitError> {
    let mut f = FieldTable::default();

    f.insert("x-single-active-consumer".into(), AMQPValue::Boolean(true));

    declare_queue(
        channel,
        name,
        Some(QueueDeclareOptions {
            durable: false,
            ..QueueDeclareOptions::default()
        }),
        Some(f),
    )
    .await
}

/// Binds a queue to an exchange
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `exchange_name` - The name of the exchange
/// * `queue_name` - The name of the queue
/// * `routing_key` - The routing key
pub async fn bind_queue(
    channel: Channel,
    exchange_name: impl Into<String>,
    queue_name: impl Into<String>,
    routing_key: impl Into<String>,
) -> Result<Channel, ImlRabbitError> {
    channel
        .queue_bind(
            &queue_name.into(),
            &exchange_name.into(),
            &routing_key.into(),
            QueueBindOptions::default(),
            FieldTable::default(),
        )
        .compat()
        .await?;

    Ok(channel)
}

pub async fn connect_to_queue(
    name: impl Into<String>,
    client: Client,
) -> Result<(Channel, Queue), ImlRabbitError> {
    let ch = create_channel(client).await?;

    declare_transient_queue(ch, name).await
}

/// Purges contents of a queue
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `queue_name` - The name of the queue
pub async fn purge_queue(
    channel: Channel,
    queue_name: impl Into<String>,
) -> Result<Channel, ImlRabbitError> {
    let name = queue_name.into();

    channel
        .queue_purge(&name, QueuePurgeOptions::default())
        .compat()
        .await?;

    tracing::info!("purged queue {}", &name);

    Ok(channel)
}

/// Starts consuming from a queue
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `queue` - The queue to use
/// * `consumer_tag` - The tag for the consumer
/// * `options` - An `Option<BasicConsumeOptions>` of additional options to pass in. If not supplied, `BasicConsumeOptions::default()` is used
pub async fn basic_consume(
    channel: Channel,
    queue: Queue,
    consumer_tag: impl Into<String>,
    options: Option<BasicConsumeOptions>,
) -> Result<impl Stream<Item = Result<message::Delivery, ImlRabbitError>>, ImlRabbitError> {
    let options = options.unwrap_or_default();

    channel
        .basic_consume(&queue, &consumer_tag.into(), options, FieldTable::default())
        .compat()
        .await
        .map(|s| s.compat().map(|x| x.map_err(|e| e.into())))
        .map_err(ImlRabbitError::from)
}

/// Publish a message to a given exchange
///
/// # Arguments
///
/// * `exhange` - The exchange to publish to
/// * `routing_key` - Where to route the message
/// * `channel` - The channel to use for publishing
/// * `msg` - The message to publish. Must implement `ToBytes + std::fmt::Debug`
pub async fn basic_publish<T: ToBytes + std::fmt::Debug>(
    channel: Channel,
    exchange: impl Into<String>,
    routing_key: impl Into<String>,
    msg: T,
) -> Result<Channel, ImlRabbitError> {
    tracing::debug!("publishing Message: {:?}", msg);

    let bytes = msg.to_bytes()?;

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
        .compat()
        .await?;

    Ok(channel)
}

/// Sends a JSON encoded message to the given exchange / queue
pub async fn send_message<T: ToBytes + std::fmt::Debug>(
    client: Client,
    exchange_name: impl Into<String>,
    queue_name: impl Into<String>,
    msg: T,
) -> Result<(), ImlRabbitError> {
    let ch = create_channel(client.clone()).await?;

    let name = queue_name.into();

    let (ch, _) = declare_transient_queue(ch, &name).await?;

    let ch = basic_publish(ch, exchange_name, name, msg).await?;

    close_channel(ch).await
}

/// Connect to the rabbitmq instance running on the IML manager
///
/// This fn is useful for production code as it reads in env vars
/// to make a connection.
///
pub async fn connect_to_rabbit() -> Result<Client, ImlRabbitError> {
    connect(
        &iml_manager_env::get_amqp_broker_url(),
        ConnectionProperties::default(),
    )
    .await
}

type ClientSender = oneshot::Sender<Client>;

/// Given a `Client`, this fn will
/// return a `(UnboundedSender, Future)` pair.
///
/// The future can be spawned on a runtime,
/// and the `UnboundedSender` can be passed a
/// `oneshot::Sender` to get a cloned connection.
///
/// This is useful for multiplexing channels over a
/// single connection.
pub fn get_cloned_conns(
    client: Client,
) -> (
    mpsc::UnboundedSender<ClientSender>,
    impl Future<Output = ()>,
) {
    let (tx, rx) = mpsc::unbounded();

    let fut = rx.for_each(move |sender: ClientSender| {
        let _ = sender.send(client.clone()).map_err(|_| {
            tracing::info!("channel recv dropped before we could hand out a connection")
        });

        future::ready(())
    });

    (tx, fut)
}

#[cfg(test)]
mod tests {
    use super::{
        basic_publish, bind_queue, connect, create_channel, declare_transient_exchange,
        declare_transient_queue, get_cloned_conns, ImlRabbitError,
    };
    use futures::{channel::oneshot, compat::Future01CompatExt, TryFutureExt};
    use lapin_futures::{
        message::BasicGetMessage, options::BasicGetOptions, Client, ConnectionProperties,
        ExchangeKind,
    };

    async fn read_message(
        exchange_name: &'static str,
        queue_name: &'static str,
    ) -> Result<Option<BasicGetMessage>, ImlRabbitError> {
        let client = create_test_connection().await?;

        let ch = create_channel(client).await?;

        let ch = declare_transient_exchange(ch, exchange_name, ExchangeKind::Direct).await?;

        let (ch, _) = declare_transient_queue(ch, queue_name.to_string()).await?;

        let ch = bind_queue(ch, exchange_name, queue_name, "").await?;

        Ok(ch
            .basic_get(
                queue_name,
                BasicGetOptions {
                    no_ack: true,
                    ..BasicGetOptions::default()
                },
            )
            .compat()
            .await?)
    }

    async fn create_test_connection() -> Result<Client, ImlRabbitError> {
        let addr = "amqp://127.0.0.1:5672//";

        connect(&addr, ConnectionProperties::default()).await
    }

    #[test]
    fn test_connect() -> Result<(), ImlRabbitError> {
        let msg = futures::executor::block_on(async {
            let client = create_test_connection().await?;

            let ch = create_channel(client).await?;

            let ch = declare_transient_exchange(ch, "foo", ExchangeKind::Direct).await?;

            let (ch, _) = declare_transient_queue(ch, "fooQ").await?;

            let ch = bind_queue(ch, "foo", "fooQ", "fooQ").await?;

            basic_publish(ch, "foo", "fooQ", "bar").await?;

            read_message("foo", "fooQ").await
        })?;

        let msg = msg.unwrap();

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"bar\"", actual);

        Ok(())
    }

    #[tokio::test]
    async fn test_get_cloned_conns() -> Result<(), ImlRabbitError> {
        let conn = create_test_connection().await?;

        let (tx, fut) = get_cloned_conns(conn);

        let (tx2, rx2) = oneshot::channel();

        tokio::spawn(fut);

        tx.unbounded_send(tx2).unwrap();

        let client = rx2.await.unwrap();

        let msg = create_channel(client)
            .and_then(|ch| declare_transient_exchange(ch, "foo2", ExchangeKind::Direct))
            .and_then(|ch| declare_transient_queue(ch, "fooQ2"))
            .and_then(move |(c, _)| bind_queue(c, "foo2", "fooQ2", "fooQ2"))
            .and_then(|ch| basic_publish(ch, "foo2", "fooQ2", "bar"))
            .and_then(|_| read_message("foo2", "fooQ2"))
            .await?;

        let msg = msg.unwrap();

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"bar\"", actual);

        let (tx2, rx2) = oneshot::channel();

        tx.unbounded_send(tx2).unwrap();

        let client = rx2.await.unwrap();

        let msg = create_channel(client)
            .and_then(|ch| basic_publish(ch, "foo2", "fooQ2", "baz"))
            .and_then(|_| read_message("foo2", "fooQ2"))
            .await?;

        let msg = msg.unwrap();

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"baz\"", actual);

        Ok(())
    }
}
