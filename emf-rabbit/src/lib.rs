// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use deadpool_lapin::{Connection, Pool};
use deadpool_lapin::{Manager, PoolError};
use emf_wire_types::ToBytes;
#[cfg(feature = "warp-filters")]
use futures::TryFutureExt;
use futures::{channel::oneshot, Stream, StreamExt};
pub use lapin::{
    message,
    options::{
        BasicConsumeOptions, BasicPublishOptions, ExchangeDeclareOptions, QueueBindOptions,
        QueueDeclareOptions, QueueDeleteOptions, QueuePurgeOptions,
    },
    types::{AMQPValue, FieldTable},
    BasicProperties, Channel, ConnectionProperties, Consumer, Error as LapinError, ExchangeKind,
    Queue,
};
use thiserror::Error;
use tokio_amqp::*;

#[cfg(feature = "warp-filters")]
use warp::Filter;

#[derive(Debug, Error)]
pub enum EmfRabbitError {
    #[error(transparent)]
    PoolError(#[from] PoolError),
    #[error(transparent)]
    LapinError(#[from] LapinError),
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::error::Error),
    #[error(transparent)]
    Utf8Error(#[from] std::str::Utf8Error),
    #[error("Consumer ended")]
    ConsumerEndedError,
    #[error(transparent)]
    OneshotCanceled(#[from] oneshot::Canceled),
}

#[cfg(feature = "warp-filters")]
impl warp::reject::Reject for EmfRabbitError {}

/// Creates a new deadpool-lapin `Pool`
/// # Arguments
///
/// * `addr` - An address to connect to
pub fn create_pool(addr: String, max_pool_size: usize, options: ConnectionProperties) -> Pool {
    let manager = Manager::new(addr, options);

    Pool::new(manager, max_pool_size)
}

pub async fn get_conn(pool: Pool) -> Result<Connection, EmfRabbitError> {
    let conn = pool.get().await?;

    Ok(conn)
}

/// Creates a channel for the passed in client
///
/// # Arguments
///
/// * `connection` - A `Connection` to create a channel on
pub async fn create_channel(connection: &Connection) -> Result<lapin::Channel, EmfRabbitError> {
    let chan = connection.create_channel().await?;

    tracing::debug!("created channel with id: {}", chan.id());

    Ok(chan)
}

/// Closes the channel
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
pub async fn close_channel(channel: &Channel) -> Result<(), EmfRabbitError> {
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
    channel: &Channel,
    name: impl Into<String>,
    exchange_kind: ExchangeKind,
    options: Option<ExchangeDeclareOptions>,
) -> Result<(), EmfRabbitError> {
    let name = name.into();
    let options = options.unwrap_or_default();

    tracing::info!("declaring exchange: {}, type: {:?}", name, exchange_kind);

    channel
        .exchange_declare(&name, exchange_kind, options, FieldTable::default())
        .await?;

    Ok(())
}

/// Declares a transient exhange if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `name` - The name of the exchange
/// * `exchange_kind` - The type of the exchange
pub async fn declare_transient_exchange(
    channel: &Channel,
    name: impl Into<String>,
    exchange_kind: ExchangeKind,
) -> Result<(), EmfRabbitError> {
    declare_exchange(
        &channel,
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
    channel: &Channel,
    name: impl Into<String>,
    options: impl Into<Option<QueueDeclareOptions>>,
    field_table: impl Into<Option<FieldTable>>,
) -> Result<Queue, EmfRabbitError> {
    let name = name.into();
    let options = options.into().unwrap_or_default();
    let field_table = field_table.into().unwrap_or_default();

    tracing::debug!("declaring queue {}", name);

    let queue = channel.queue_declare(&name, options, field_table).await?;

    Ok(queue)
}

/// Declares a transient queue if it does not already exist.
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `name` - The name of the queue
pub async fn declare_transient_queue(
    channel: &Channel,
    name: impl Into<String>,
) -> Result<Queue, EmfRabbitError> {
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
    channel: &Channel,
    exchange_name: impl Into<String>,
    queue_name: impl Into<String>,
    routing_key: impl Into<String>,
) -> Result<(), EmfRabbitError> {
    channel
        .queue_bind(
            &queue_name.into(),
            &exchange_name.into(),
            &routing_key.into(),
            QueueBindOptions::default(),
            FieldTable::default(),
        )
        .await?;

    Ok(())
}

pub async fn connect_to_queue(
    name: impl Into<String>,
    ch: &Channel,
) -> Result<Queue, EmfRabbitError> {
    declare_transient_queue(ch, name).await
}

/// Purges contents of a queue
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `queue_name` - The name of the queue
pub async fn purge_queue(
    channel: &Channel,
    queue_name: impl Into<String>,
) -> Result<(), EmfRabbitError> {
    let name = queue_name.into();

    channel
        .queue_purge(&name, QueuePurgeOptions::default())
        .await?;

    tracing::info!("purged queue {}", &name);

    Ok(())
}

pub async fn delete_queue(
    channel: &Channel,
    queue_name: impl Into<String>,
) -> Result<(), EmfRabbitError> {
    let name = queue_name.into();

    channel
        .queue_delete(&name, QueueDeleteOptions::default())
        .await?;

    tracing::info!("queue {} deleted", &name);

    Ok(())
}

/// Starts consuming from a queue
///
/// *Note*: The `channel` parameter is borrowed. If it was owned it would be dropped which will cause the consumer to finish.
///
/// # Arguments
///
/// * `channel` - The `Channel` to use
/// * `queue` - The queue to use
/// * `consumer_tag` - The tag for the consumer
/// * `options` - An `Option<BasicConsumeOptions>` of additional options to pass in. If not supplied, `BasicConsumeOptions::default()` is used
pub async fn basic_consume(
    channel: &Channel,
    queue: Queue,
    consumer_tag: impl Into<String>,
    options: Option<BasicConsumeOptions>,
) -> Result<impl Stream<Item = Result<(Channel, message::Delivery), EmfRabbitError>>, EmfRabbitError>
{
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
        .map_err(EmfRabbitError::from)
}

pub async fn basic_consume_one(
    channel: &Channel,
    queue: Queue,
    consumer_tag: impl Into<String>,
    options: Option<BasicConsumeOptions>,
) -> Result<(Channel, message::Delivery), EmfRabbitError> {
    let options = options.unwrap_or_default();

    let (x, _) = channel
        .basic_consume(
            queue.name().as_str(),
            &consumer_tag.into(),
            options,
            FieldTable::default(),
        )
        .await?
        .map(|x| x.map_err(EmfRabbitError::from))
        .into_future()
        .await;

    let x = x.transpose()?;
    let x = x.ok_or(EmfRabbitError::ConsumerEndedError)?;

    Ok(x)
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
    channel: &Channel,
    exchange: impl Into<String>,
    routing_key: impl Into<String>,
    msg: T,
) -> Result<(), EmfRabbitError> {
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

    Ok(())
}

/// Sends a JSON encoded message to the given exchange / queue
pub async fn send_message<T: ToBytes + std::fmt::Debug>(
    ch: &Channel,
    exchange_name: impl Into<String>,
    queue_name: impl Into<String>,
    msg: T,
) -> Result<(), EmfRabbitError> {
    let name = queue_name.into();

    declare_transient_queue(&ch, &name).await?;

    basic_publish(ch, exchange_name, name, msg).await?;

    Ok(())
}

/// Connect to the rabbitmq instance running on the EMF manager
///
/// This fn is useful for production code as it reads in env vars
/// to make a connection.
///
pub fn connect_to_rabbit(max_pool_size: usize) -> Pool {
    create_pool(
        emf_manager_env::get_amqp_broker_url(),
        max_pool_size,
        ConnectionProperties::default().with_tokio(),
    )
}

/// Creates a warp `Filter` that will hand out
/// a connection from the pool for each request.
///
/// Since connections are pooled, it is important to drop the connection ASAP
/// To avoid delays
#[cfg(feature = "warp-filters")]
pub fn create_connection_filter(
    pool: Pool,
) -> impl Filter<Extract = (deadpool_lapin::Connection,), Error = warp::Rejection> + Clone {
    warp::any().and_then(move || {
        let pool = pool.clone();

        async move {
            let conn = pool
                .get()
                .map_err(EmfRabbitError::from)
                .map_err(warp::reject::custom)
                .await?;

            Ok::<_, warp::Rejection>(conn)
        }
    })
}

#[cfg(test)]
mod tests {
    use super::{
        basic_consume, basic_publish, bind_queue, create_channel, create_pool,
        declare_transient_exchange, declare_transient_queue, get_conn, BasicConsumeOptions,
        EmfRabbitError,
    };
    use deadpool_lapin::Pool;
    use futures::TryStreamExt;
    use lapin::{
        message::BasicGetMessage, options::BasicGetOptions, ConnectionProperties, ExchangeKind,
    };

    async fn read_message(
        exchange_name: &'static str,
        queue_name: &'static str,
    ) -> Result<Option<BasicGetMessage>, EmfRabbitError> {
        let pool = create_test_pool();

        let conn = get_conn(pool).await?;

        let ch = create_channel(&conn).await?;

        declare_transient_exchange(&ch, exchange_name, ExchangeKind::Direct).await?;

        declare_transient_queue(&ch, queue_name.to_string()).await?;

        bind_queue(&ch, exchange_name, queue_name, "").await?;

        Ok(ch
            .basic_get(queue_name, BasicGetOptions { no_ack: true })
            .await?)
    }

    fn create_test_pool() -> Pool {
        let addr = "amqp://127.0.0.1:5672//";

        create_pool(addr.to_string(), 2, ConnectionProperties::default())
    }

    #[test]
    fn test_connect() -> Result<(), EmfRabbitError> {
        let msg = futures::executor::block_on(async {
            let pool = create_test_pool();

            let conn = get_conn(pool).await?;

            let ch = create_channel(&conn).await?;

            declare_transient_exchange(&ch, "foo", ExchangeKind::Direct).await?;

            declare_transient_queue(&ch, "fooQ").await?;

            bind_queue(&ch, "foo", "fooQ", "fooQ").await?;

            basic_publish(&ch, "foo", "fooQ", "bar").await?;

            read_message("foo", "fooQ").await
        })?;

        let msg = msg.unwrap();

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"bar\"", actual);

        Ok(())
    }

    #[tokio::test]
    async fn test_connection_filter() -> Result<(), EmfRabbitError> {
        use crate::create_connection_filter;

        let pool = create_test_pool();

        let filter = create_connection_filter(pool.clone());

        let conn = warp::test::request().filter(&filter).await.unwrap();

        let status = pool.status();

        assert_eq!(status.size, 1);
        assert_eq!(status.available, 0);

        let ch = create_channel(&conn).await?;

        declare_transient_exchange(&ch, "foo2", ExchangeKind::Direct).await?;

        declare_transient_queue(&ch, "fooQ2").await?;

        bind_queue(&ch, "foo2", "fooQ2", "fooQ2").await?;

        basic_publish(&ch, "foo2", "fooQ2", "bar").await?;

        let msg = read_message("foo2", "fooQ2").await?.unwrap();

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"bar\"", actual);

        let conn2 = warp::test::request().filter(&filter).await.unwrap();

        let status = pool.status();

        assert_eq!(status.size, 2);
        assert_eq!(status.available, 0);

        let ch = create_channel(&conn2).await?;

        basic_publish(&ch, "foo2", "fooQ2", "baz").await?;

        let msg = read_message("foo2", "fooQ2").await?.unwrap();

        let actual = std::str::from_utf8(&msg.delivery.data)?;

        assert_eq!("\"baz\"", actual);

        drop(conn);

        let status = pool.status();

        assert_eq!(status.size, 2);
        assert_eq!(status.available, 1);

        drop(conn2);

        let status = pool.status();

        assert_eq!(status.size, 2);
        assert_eq!(status.available, 2);

        Ok(())
    }

    #[tokio::test(core_threads = 2)]
    async fn test_consume_queue() -> Result<(), Box<dyn std::error::Error>> {
        let pool = create_test_pool();

        let conn = get_conn(pool).await?;

        let ch = create_channel(&conn).await?;

        declare_transient_exchange(&ch, "foo3", ExchangeKind::Direct).await?;

        let q = declare_transient_queue(&ch, "fooQ3").await?;

        bind_queue(&ch, "foo3", "fooQ3", "fooQ3").await?;

        basic_publish(&ch, "foo3", "fooQ3", 1).await?;

        let mut consumer = basic_consume(
            &ch,
            q,
            "fooQ3",
            Some(BasicConsumeOptions {
                no_ack: true,
                ..BasicConsumeOptions::default()
            }),
        )
        .await?;

        let x = tokio::spawn(async move {
            let mut x = String::new();

            while let Some((ch, delivery)) = consumer.try_next().await? {
                ch.close(200, "OK").await?;

                x = std::str::from_utf8(&delivery.data).unwrap().to_string();
            }

            Ok::<String, EmfRabbitError>(x)
        })
        .await??;

        assert_eq!(x, "1".to_string());

        Ok(())
    }
}
