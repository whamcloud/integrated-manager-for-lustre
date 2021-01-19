// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_agent_comms::{
    error::EmfAgentCommsError,
    flush_queue,
    host::{self, SharedHosts},
    messaging::{consume_agent_tx_queue, AgentData, AGENT_TX_RUST},
    session::{self, Session, Sessions},
};
use emf_rabbit::{self, create_connection_filter, send_message, Channel, Connection};
use emf_wire_types::{
    Envelope, Fqdn, ManagerMessage, ManagerMessages, Message, PluginMessage, PluginName,
};
use futures::{channel::oneshot, FutureExt, TryFutureExt, TryStreamExt};
use std::{sync::Arc, time::Duration};
use warp::Filter;

async fn data_handler(
    has_session: bool,
    ch: Channel,
    data: AgentData,
) -> Result<(), EmfAgentCommsError> {
    if has_session {
        tracing::debug!("Forwarding valid message {}", data);

        let s = format!("rust_agent_{}_rx", data.plugin);

        send_message(&ch, "", s, PluginMessage::from(data)).await?;
    } else {
        tracing::warn!("Terminating session because unknown {}", data);

        send_message(
            &ch,
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
    ch: Channel,
    fqdn: Fqdn,
    plugin: PluginName,
) -> Result<(), EmfAgentCommsError> {
    let session = Session::new(plugin.clone(), fqdn.clone());

    tracing::info!("Creating session {}", session);

    let last_opt = sessions.insert(plugin.clone(), session.clone());

    if let Some(last) = last_opt {
        tracing::warn!("Destroying session {} to create new one", last);

        let s = format!("rust_agent_{}_rx", plugin);

        send_message(
            &ch,
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
        &ch,
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
        &ch,
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

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    emf_tracing::init();

    // Handle an error in locks by shutting down
    let (tx, rx) = oneshot::channel();

    let shared_hosts = host::shared_hosts();
    let shared_hosts2 = Arc::clone(&shared_hosts);
    let shared_hosts3 = Arc::clone(&shared_hosts);

    let pool = emf_rabbit::connect_to_rabbit(2);

    let conn = emf_rabbit::get_conn(pool.clone()).await?;

    tokio::spawn(
        async move {
            let ch = emf_rabbit::create_channel(&conn).await?;

            drop(conn);

            let mut s = consume_agent_tx_queue(&ch, AGENT_TX_RUST).await?;

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
        .unwrap_or_else(|e: EmfAgentCommsError| {
            tx.send(()).unwrap_or_else(drop);
            tracing::error!("{:?}", e)
        }),
    );

    let hosts_filter = warp::any().map(move || Arc::clone(&shared_hosts2));

    let receiver = warp::post()
        .and(warp::header::<String>("x-ssl-client-name").map(Fqdn))
        .and(hosts_filter)
        .and(create_connection_filter(pool))
        .and(warp::body::json())
        .and_then(
            |fqdn: Fqdn,
             hosts: SharedHosts,
             conn: Connection,
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

                    let ch = emf_rabbit::create_channel(&conn).await?;

                    drop(conn);

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
                                    ch.clone(),
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
                                session_create_req_handler(&mut lock, ch.clone(), fqdn, plugin)
                                    .await?;
                            }
                        }
                    }

                    emf_rabbit::close_channel(&ch).await?;

                    Ok::<(), EmfAgentCommsError>(())
                }
                .map_err(warp::reject::custom)
                .map_ok(|_| {
                    warp::reply::with_status(warp::reply(), warp::http::StatusCode::ACCEPTED)
                })
            },
        );

    let hosts_filter = warp::any().map(move || Arc::clone(&shared_hosts3));

    let sender = warp::get()
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

                        return Ok::<_, EmfAgentCommsError>(ManagerMessages {
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
                    .map(|x| serde_json::from_slice(&x).map_err(EmfAgentCommsError::from))
                    .collect::<Result<Vec<_>, EmfAgentCommsError>>()?;

                let guard = sessions.lock().await;

                xs.retain(|x| session::is_session_valid(x, &guard));

                tracing::debug!(
                    "--> Delivery to agent {}({:?}): {:?}",
                    &fqdn,
                    &args.client_start_time,
                    xs,
                );

                Ok::<_, EmfAgentCommsError>(ManagerMessages { messages: xs })
            }
            .map_err(warp::reject::custom)
        })
        .map(|envelope| warp::reply::json(&envelope));

    let log = warp::log("emf_agent_comms::api");

    let routes = warp::path("message").and(receiver.or(sender).with(log));

    let addr = emf_manager_env::get_http_agent2_addr();

    tracing::info!("Starting emf-agent-comms on {:?}", addr);

    let (_, fut) = warp::serve(routes).bind_with_graceful_shutdown(addr, rx.map(drop));

    fut.await;

    Ok(())
}
