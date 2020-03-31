// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{
    channel::{mpsc, oneshot},
    future, Future, Stream, StreamExt, TryFutureExt,
};
use iml_manager_env;
use iml_wire_types::ToBytes;
pub use lapin::{
    message,
    options::{
        BasicConsumeOptions, BasicPublishOptions, ExchangeDeclareOptions, QueueBindOptions,
        QueueDeclareOptions, QueueDeleteOptions, QueuePurgeOptions,
    },
    types::{AMQPValue, FieldTable},
    BasicProperties, Channel, Connection, ConnectionProperties, Consumer, Error as LapinError,
    ExchangeKind, Queue,
};

#[cfg(feature = "warp-filters")]
use warp::Filter;

#[derive(Debug)]
pub enum ImlRabbitError {
    LapinError(LapinError),
    SerdeJsonError(serde_json::error::Error),
    Utf8Error(std::str::Utf8Error),
    ConsumerEndedError,
    OneshotCanceled(oneshot::Canceled),
}

#[cfg(feature = "warp-filters")]
impl warp::reject::Reject for ImlRabbitError {}

impl std::fmt::Display for ImlRabbitError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlRabbitError::LapinError(ref err) => write!(f, "{}", err),
            ImlRabbitError::SerdeJsonError(ref err) => write!(f, "{}", err),
            ImlRabbitError::Utf8Error(ref err) => write!(f, "{}", err),
            ImlRabbitError::ConsumerEndedError => write!(f, "Consumer ended"),
            ImlRabbitError::OneshotCanceled(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlRabbitError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlRabbitError::LapinError(ref err) => Some(err),
            ImlRabbitError::SerdeJsonError(ref err) => Some(err),
            ImlRabbitError::Utf8Error(ref err) => Some(err),
            ImlRabbitError::OneshotCanceled(ref err) => Some(err),
            ImlRabbitError::ConsumerEndedError => None,
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

impl From<oneshot::Canceled> for ImlRabbitError {
    fn from(err: oneshot::Canceled) -> Self {
        ImlRabbitError::OneshotCanceled(err)
    }
}

/// Connects to an AMQP server
///
/// # Arguments
///
/// * `addr` - An address to connect to
/// * `opts` - `ConnectionProperties` to configure the connection
pub async fn connect(
    addr: &str,
    options: ConnectionProperties,
) -> Result<Connection, ImlRabbitError> {
    Connection::connect(addr, options)
        .await
        .map_err(ImlRabbitError::from)
}

pub trait ChannelFuture: Future<Output = Result<Channel, LapinError>> {}
impl<T: Future<Output = Result<Channel, LapinError>>> ChannelFuture for T {}

/// Creates a channel for the passed in client
///
/// # Arguments
///
/// * `connection` - A `Connection` to create a channel on
pub async fn create_channel(connection: &Connection) -> Result<lapin::Channel, ImlRabbitError> {
    let chan = connection.create_channel().await?;

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

    channel.close(200, "OK").await?;

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
    channel: Channel,
    name: impl Into<String>,
    exchange_kind: ExchangeKind,
    options: Option<ExchangeDeclareOptions>,
) -> Result<Channel, ImlRabbitError> {
    let name = name.into();
    let options = options.unwrap_or_default();

    tracing::info!("declaring exchange: {}, type: {:?}", name, exchange_kind);

    channel
        .exchange_declare(&name, exchange_kind, options, FieldTable::default())
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
    channel: Channel,
    name: impl Into<String>,
    exchange_kind: ExchangeKind,
) -> Result<Channel, ImlRabbitError> {
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
    options: impl Into<Option<QueueDeclareOptions>>,
    field_table: impl Into<Option<FieldTable>>,
) -> Result<(Channel, Queue), ImlRabbitError> {
    let name = name.into();
    let options = options.into().unwrap_or_default();
    let field_table = field_table.into().unwrap_or_default();

    tracing::debug!("declaring queue {}", name);

    let queue = channel.queue_declare(&name, options, field_table).await?;

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
        QueueDeclareOptions {
            durable: false,
            ..QueueDeclareOptions::default()
        },
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
        .await?;

    Ok(channel)
}

pub async fn connect_to_queue(
    name: impl Into<String>,
    conn: Connection,
) -> Result<(Channel, Queue), ImlRabbitError> {
    let ch = create_channel(&conn).await?;

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
        .await?;

    tracing::info!("purged queue {}", &name);

    Ok(channel)
}

pub async fn delete_queue(
    channel: Channel,
    queue_name: impl Into<String>,
) -> Result<Channel, ImlRabbitError> {
    let name = queue_name.into();

    channel
        .queue_delete(&name, QueueDeleteOptions::default())
        .await?;

    tracing::info!("queue {} deleted", &name);

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
        .basic_consume(
            queue.name().as_str(),
            &consumer_tag.into(),
            options,
            FieldTable::default(),
        )
        .await
        .map(|s| s.map(|x| x.map_err(|e| e.into())))
        .map_err(ImlRabbitError::from)
}

pub async fn basic_consume_one(
    channel: Channel,
    queue: Queue,
    consumer_tag: impl Into<String>,
    options: Option<BasicConsumeOptions>,
) -> Result<(message::Delivery, Channel), ImlRabbitError> {
    let options = options.unwrap_or_default();

    let (x, _) = channel
        .basic_consume(
            queue.name().as_str(),
            &consumer_tag.into(),
            options,
            FieldTable::default(),
        )
        .await?
        .map(|x| x.map_err(ImlRabbitError::from))
        .into_future()
        .await;

    let x = x.transpose()?;
    let x = x.ok_or_else(|| ImlRabbitError::ConsumerEndedError)?;

    Ok((x, channel))
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
            BasicPublishOptions::default(),
            bytes,
            BasicProperties::default()
                .with_content_type("application/json".into())
                .with_content_encoding("utf-8".into())
                .with_priority(0),
        )
        .await?;

    Ok(channel)
}

/// Sends a JSON encoded message to the given exchange / queue
pub async fn send_message<T: ToBytes + std::fmt::Debug>(
    conn: Connection,
    exchange_name: impl Into<String>,
    queue_name: impl Into<String>,
    msg: T,
) -> Result<(), ImlRabbitError> {
    let ch = create_channel(&conn).await?;

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
pub async fn connect_to_rabbit() -> Result<Connection, ImlRabbitError> {
    connect(
        &iml_manager_env::get_amqp_broker_url(),
        ConnectionProperties::default(),
    )
    .await
}

type ConnectionSender = oneshot::Sender<Connection>;

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
    conn: Connection,
) -> (
    mpsc::UnboundedSender<ConnectionSender>,
    impl Future<Output = ()>,
) {
    let (tx, rx) = mpsc::unbounded();

    let fut = rx.for_each(move |sender: ConnectionSender| {
        let _ = sender.send(conn.clone()).map_err(|_| {
            tracing::info!("channel recv dropped before we could hand out a connection")
        });

        future::ready(())
    });

    (tx, fut)
}

/// Creates a warp `Filter` that will hand out
/// a cloned client for each request.
#[cfg(feature = "warp-filters")]
pub async fn create_connection_filter() -> Result<
    (
        impl Future<Output = ()>,
        impl Filter<Extract = (Connection,), Error = warp::Rejection> + Clone,
    ),
    ImlRabbitError,
> {
    let conn = connect_to_rabbit().await?;

    let (tx, fut) = get_cloned_conns(conn);

    let filter = warp::any().and_then(move || {
        let (tx2, rx2) = oneshot::channel();

        tx.unbounded_send(tx2).unwrap();

        rx2.map_err(ImlRabbitError::OneshotCanceled)
            .map_err(warp::reject::custom)
    });

    Ok((fut, filter))
}

#[cfg(test)]
mod tests {
    use super::{
        basic_publish, bind_queue, connect, create_channel, declare_transient_exchange,
        declare_transient_queue, get_cloned_conns, ImlRabbitError,
    };
    use futures::{channel::oneshot, TryFutureExt};
    use lapin::{
        message::BasicGetMessage, options::BasicGetOptions, Connection, ConnectionProperties,
        ExchangeKind,
    };

    async fn read_message(
        exchange_name: &'static str,
        queue_name: &'static str,
    ) -> Result<Option<BasicGetMessage>, ImlRabbitError> {
        let conn = create_test_connection().await?;

        let ch = create_channel(&conn).await?;

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
            .await?)
    }

    async fn create_test_connection() -> Result<Connection, ImlRabbitError> {
        let addr = "amqp://127.0.0.1:5672//";

        connect(&addr, ConnectionProperties::default()).await
    }

    #[test]
    fn test_connect() -> Result<(), ImlRabbitError> {
        let msg = futures::executor::block_on(async {
            let conn = create_test_connection().await?;

            let ch = create_channel(&conn).await?;

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

        let conn = rx2.await.unwrap();

        let msg = create_channel(&conn)
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

        let msg = create_channel(&client)
            .and_then(|ch| basic_publish(ch, "foo2", "fooQ2", "baz"))
            .and_then(|_| read_message("foo2", "fooQ2"))
            .await?;

        let msg = msg.unwrap();

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"baz\"", actual);

        Ok(())
    }
}
