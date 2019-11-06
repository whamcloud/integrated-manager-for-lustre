// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{channel::oneshot, Future, FutureExt, TryFutureExt, TryStreamExt};
use iml_agent_comms::{
    error::ImlAgentCommsError,
    flush_queue,
    host::{self, SharedHosts},
    messaging::{consume_agent_tx_queue, AgentData, AGENT_TX_RUST},
    session::{self, Session, Sessions},
};
use iml_rabbit::{self, send_message, Client};
use iml_wire_types::{
    Envelope, Fqdn, ManagerMessage, ManagerMessages, Message, PluginMessage, PluginName,
};
use std::{sync::Arc, time::Duration};
use tracing_subscriber::{fmt::Subscriber, EnvFilter};
use warp::Filter;

async fn data_handler(
    has_session: bool,
    client: Client,
    data: AgentData,
) -> Result<(), ImlAgentCommsError> {
    if has_session {
        tracing::debug!("Forwarding valid message {}", data);

        let s = format!("rust_agent_{}_rx", data.plugin);

        send_message(client, "", s, PluginMessage::from(data)).await?;
    } else {
        tracing::warn!("Terminating session because unknown {}", data);

        send_message(
            client.clone(),
            "",
            AGENT_TX_RUST,
            ManagerMessage::SessionTerminate {
                fqdn: data.fqdn,
                plugin: data.plugin,
                session_id: data.session_id,
            },
        )
        .await?;
    }

    Ok(())
}

async fn session_create_req_handler(
    sessions: &mut Sessions,
    client: Client,
    fqdn: Fqdn,
    plugin: PluginName,
) -> Result<(), ImlAgentCommsError> {
    let session = Session::new(plugin.clone(), fqdn.clone());

    tracing::info!("Creating session {}", session);

    let last_opt = sessions.insert(plugin.clone(), session.clone());

    if let Some(last) = last_opt {
        tracing::warn!("Destroying session {} to create new one", last);

        let s = format!("rust_agent_{}_rx", plugin);

        send_message(
            client.clone(),
            "",
            s,
            PluginMessage::SessionTerminate {
                fqdn: last.fqdn,
                plugin: last.plugin,
                session_id: last.id,
            },
        )
        .await?;
    }

    let s = format!("rust_agent_{}_rx", plugin.clone());

    send_message(
        client.clone(),
        "",
        s,
        PluginMessage::SessionCreate {
            fqdn: fqdn.clone(),
            plugin: plugin.clone(),
            session_id: session.id.clone(),
        },
    )
    .await?;

    send_message(
        client.clone(),
        "",
        AGENT_TX_RUST,
        ManagerMessage::SessionCreateResponse {
            fqdn,
            plugin,
            session_id: session.id,
        },
    )
    .await?;

    Ok(())
}

#[derive(serde::Deserialize, serde::Serialize, Debug)]
struct GetArgs {
    server_boot_time: String,
    client_start_time: String,
}

#[derive(serde::Deserialize, Debug)]
struct MessageFqdn {
    pub fqdn: Fqdn,
}

/// Creates a warp `Filter` that will hand out
/// a cloned client for each request.
pub async fn create_client_filter() -> Result<
    (
        impl Future<Output = ()>,
        impl Filter<Extract = (Client,), Error = warp::Rejection> + Clone,
    ),
    ImlAgentCommsError,
> {
    let conn = iml_rabbit::connect_to_rabbit().await?;

    let (tx, fut) = iml_rabbit::get_cloned_conns(conn);

    let filter = warp::any().and_then(move || {
        let (tx2, rx2) = oneshot::channel();

        tx.unbounded_send(tx2).unwrap();

        rx2.map_err(warp::reject::custom)
    });

    Ok((fut, filter))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let subscriber = Subscriber::builder()
        .with_env_filter(EnvFilter::from_default_env())
        .finish();

    tracing::subscriber::set_global_default(subscriber).unwrap();

    // Handle an error in locks by shutting down
    let (tx, rx) = oneshot::channel();

    let shared_hosts = host::shared_hosts();
    let shared_hosts2 = Arc::clone(&shared_hosts);
    let shared_hosts3 = Arc::clone(&shared_hosts);

    tokio::spawn(
        async move {
            let conn = iml_rabbit::connect_to_rabbit().await?;

            let ch = iml_rabbit::create_channel(conn).await?;

            let mut s = consume_agent_tx_queue(ch, AGENT_TX_RUST).await?;

            while let Some(msg) = s.try_next().await? {
                let MessageFqdn { fqdn } = serde_json::from_slice(&msg.data)?;

                let mut hosts = shared_hosts.lock().await;
                let host = hosts.get_mut(&fqdn);

                if let Some(host) = host {
                    let mut queue = host.queue.lock().await;
                    queue.push_back(msg.data);

                    tracing::debug!(
                        "Put data on host queue {}: Queue size: {:?}",
                        fqdn,
                        queue.len()
                    );
                } else {
                    tracing::warn!(
                        "Dropping message to {:?} because it did not have a host queue",
                        fqdn
                    );
                }
            }

            Ok(())
        }
        .unwrap_or_else(|e: ImlAgentCommsError| {
            tx.send(()).unwrap_or_else(drop);
            tracing::error!("{:?}", e)
        }),
    );

    let hosts_filter = warp::any().map(move || Arc::clone(&shared_hosts2));

    let (fut, client_filter) = create_client_filter().await?;

    tokio::spawn(fut);

    let receiver = warp::post2()
        .and(warp::header::<String>("x-ssl-client-name").map(Fqdn))
        .and(hosts_filter)
        .and(client_filter)
        .and(warp::body::json())
        .and_then(
            |fqdn: Fqdn,
             hosts: SharedHosts,
             client: Client,
             Envelope {
                 messages,
                 client_start_time,
                 ..
             }: Envelope| {
                async move {
                    tracing::debug!("<-- Delivery from agent {}: Messages: {:?}", fqdn, messages,);

                    let sessions = {
                        let mut hosts = hosts.lock().await;

                        let host = host::get_or_insert(&mut hosts, fqdn, client_start_time);

                        Arc::clone(&host.sessions)
                    };

                    for msg in messages {
                        let s2 = Arc::clone(&sessions);

                        match msg {
                            Message::Data {
                                plugin,
                                session_id,
                                session_seq,
                                body,
                                fqdn,
                                ..
                            } => {
                                let lock = s2.lock().await;

                                let has_session =
                                    session::get_by_session_id(&plugin, &session_id, &lock)
                                        .is_some();

                                data_handler(
                                    has_session,
                                    client.clone(),
                                    AgentData {
                                        fqdn,
                                        plugin,
                                        session_id,
                                        session_seq,
                                        body,
                                    },
                                )
                                .await?;
                            }
                            Message::SessionCreateRequest { plugin, fqdn } => {
                                let mut lock = s2.lock().await;
                                session_create_req_handler(&mut lock, client.clone(), fqdn, plugin)
                                    .await?;
                            }
                        }
                    }

                    Ok::<(), ImlAgentCommsError>(())
                }
                .map_err(warp::reject::custom)
                .map_ok(|_| {
                    warp::reply::with_status(warp::reply(), warp::http::StatusCode::ACCEPTED)
                })
            },
        );

    let hosts_filter = warp::any().map(move || Arc::clone(&shared_hosts3));

    let sender = warp::get2()
        .and(warp::header::<String>("x-ssl-client-name").map(Fqdn))
        .and(warp::query::<GetArgs>())
        .and(hosts_filter)
        .and_then(|fqdn: Fqdn, args: GetArgs, hosts: SharedHosts| {
            async move {
                {
                    let mut hosts = hosts.lock().await;
                    let mut host = host::get_or_insert(
                        &mut hosts,
                        fqdn.clone(),
                        args.client_start_time.clone(),
                    );

                    host.stop();

                    // If we are not dealing with the same agent anymore, terminate all existing sessions.
                    if host.client_start_time != args.client_start_time {
                        tracing::info!(
                            "Terminating all sessions on {:?} because start time has changed",
                            fqdn
                        );

                        host.client_start_time = args.client_start_time;

                        return Ok::<_, ImlAgentCommsError>(ManagerMessages {
                            messages: vec![ManagerMessage::SessionTerminateAll { fqdn }],
                        });
                    }
                }

                let (tx, rx) = oneshot::channel();

                let (sessions, queue) = {
                    let mut hosts = hosts.lock().await;

                    let host = host::get_or_insert(
                        &mut hosts,
                        fqdn.clone(),
                        args.client_start_time.clone(),
                    );

                    host.stop_reading = Some(tx);

                    (Arc::clone(&host.sessions), Arc::clone(&host.queue))
                };

                let xs = flush_queue::flush(queue, Duration::from_secs(30), rx).await?;

                let mut xs: Vec<ManagerMessage> = xs
                    .into_iter()
                    .map(|x| serde_json::from_slice(&x).map_err(ImlAgentCommsError::from))
                    .collect::<Result<Vec<_>, ImlAgentCommsError>>()?;

                let guard = sessions.lock().await;

                xs.retain(|x| session::is_session_valid(x, &guard));

                tracing::debug!(
                    "--> Delivery to agent {}({:?}): {:?}",
                    &fqdn,
                    &args.client_start_time,
                    xs,
                );

                Ok::<_, ImlAgentCommsError>(ManagerMessages { messages: xs })
            }
            .map_err(warp::reject::custom)
        })
        .map(|envelope| warp::reply::json(&envelope));

    let log = warp::log("iml_agent_comms::api");

    let routes = warp::path("message").and(receiver.or(sender).with(log));

    let addr = iml_manager_env::get_http_agent2_addr();

    tracing::info!("Starting iml-agent-comms on {:?}", addr);

    let (_, fut) = warp::serve(routes).bind_with_graceful_shutdown(addr, rx.map(drop));

    fut.await;

    Ok(())
}
