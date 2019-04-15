// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use futures::{
    future::{self, lazy, Either},
    prelude::*,
    stream,
    sync::oneshot,
};
use iml_agent_comms::{
    flush_queue,
    host::{self, SharedHosts},
    messaging::{consume_agent_tx_queue, AgentData, AGENT_TX_RUST},
    session::{self, Session, Sessions},
};
use iml_rabbit::{self, send_message, TcpClient};
use iml_wire_types::{
    Envelope, Fqdn, ManagerMessage, ManagerMessages, Message, PluginMessage, PluginName,
};
use std::{sync::Arc, time::Duration};
use tokio;
use warp::Filter;

fn data_handler(
    sessions: Sessions,
    client: TcpClient,
    data: AgentData,
) -> impl Future<Item = (), Error = failure::Error> {
    let has_key = sessions.lock().contains_key(&data.plugin);

    if has_key {
        log::debug!("Forwarding valid message {}", data);

        Either::A(send_message(
            client.clone(),
            "",
            format!("rust_agent_{}_rx", data.plugin),
            PluginMessage::from(data),
        ))
    } else {
        log::warn!("Terminating session because unknown {}", data);

        Either::B(send_message(
            client.clone(),
            "",
            AGENT_TX_RUST,
            ManagerMessage::SessionTerminate {
                fqdn: data.fqdn.clone(),
                plugin: data.plugin.clone(),
                session_id: data.session_id,
            },
        ))
    }
}

fn session_create_req_handler(
    sessions: Sessions,
    client: TcpClient,
    fqdn: Fqdn,
    plugin: PluginName,
) -> impl Future<Item = (), Error = failure::Error> {
    let session = Session::new(plugin.clone(), fqdn.clone());

    log::info!("Creating session {}", session);

    let last = sessions.lock().insert(plugin.clone(), session.clone());

    let fut = if let Some(last) = last {
        log::warn!("Destroying session {} to create new one", last);

        Either::A(send_message(
            client.clone(),
            "",
            format!("rust_agent_{}_rx", plugin),
            PluginMessage::SessionTerminate {
                fqdn: last.fqdn,
                plugin: last.plugin,
                session_id: last.id,
            },
        ))
    } else {
        Either::B(future::ok(()))
    };

    fut.and_then(move |_| {
        send_message(
            client.clone(),
            "",
            format!("rust_agent_{}_rx", plugin.clone()),
            PluginMessage::SessionCreate {
                fqdn: fqdn.clone(),
                plugin: plugin.clone(),
                session_id: session.id.clone(),
            },
        )
        .map(|_| (client, fqdn, plugin, session.id))
    })
    .and_then(move |(client, fqdn, plugin, session_id)| {
        send_message(
            client.clone(),
            "",
            AGENT_TX_RUST,
            ManagerMessage::SessionCreateResponse {
                fqdn,
                plugin,
                session_id,
            },
        )
    })
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

fn main() {
    env_logger::init();

    // Handle an error in locks by shutting down
    let (tx, rx) = oneshot::channel();

    let hosts_state = host::shared_hosts();
    let hosts_state2 = Arc::clone(&hosts_state);
    let hosts_state3 = Arc::clone(&hosts_state);

    tokio::run(lazy(move || {
        tokio::spawn(lazy(move || {
            iml_rabbit::connect_to_rabbit()
                .and_then(iml_rabbit::create_channel)
                .and_then(|ch| consume_agent_tx_queue(ch, AGENT_TX_RUST))
                .and_then(move |stream| {
                    log::info!("Started consuming agent_tx queue");

                    stream.from_err().for_each(move |msg| {
                        let MessageFqdn { fqdn } = serde_json::from_slice(&msg.data)?;

                        let hosts_state = hosts_state.lock();
                        let host = hosts_state.get(&fqdn);

                        if let Some(host) = host {
                            host.queue.lock().push_back(msg.data);
                            log::debug!(
                                "Put data on host queue {:?}: Queue size: {:?}",
                                fqdn,
                                host.queue.lock().len()
                            );
                        } else {
                            log::warn!(
                                "Dropping message to {:?} because it did not have a host queue",
                                fqdn
                            );
                        }

                        Ok(())
                    })
                })
                .map_err(|e| {
                    let _ = tx.send(());
                    log::error!("{:?}", e)
                })
        }));

        let hosts = warp::any().map(move || Arc::clone(&hosts_state2));

        /// Creates a warp `Filter` that will hand out
        /// a cloned client for each request.
        pub fn create_client_filter() -> (
            impl Future<Item = (), Error = ()>,
            impl Filter<Extract = (TcpClient,), Error = warp::Rejection> + Clone,
        ) {
            let (tx, fut) = iml_rabbit::get_cloned_conns(iml_rabbit::connect_to_rabbit());

            let filter = warp::any().and_then(move || {
                let (tx2, rx2) = oneshot::channel();

                tx.unbounded_send(tx2).unwrap();

                rx2.map_err(warp::reject::custom)
            });

            (fut, filter)
        }

        let (fut, client_filter) = create_client_filter();

        tokio::spawn(fut);

        let receiver = warp::post2()
            .and(warp::header::<String>("x-ssl-client-name").map(Fqdn))
            .and(hosts)
            .and(client_filter)
            .and(warp::body::json())
            .and_then(
                |fqdn: Fqdn, hosts: SharedHosts, client: TcpClient, envelope: Envelope| {
                    log::debug!(
                        "MessageView.post: {:?}, {:?} Messages, Envelope: {:?}",
                        fqdn,
                        envelope.messages.len(),
                        envelope
                    );

                    // If we are not dealing with the same agent anymore, remove the host.
                    let sessions = {
                        let mut hosts = hosts.lock();
                        host::remove_stale(&mut hosts, &fqdn, &envelope.client_start_time);
                        let host =
                            host::get_or_insert(&mut hosts, fqdn, envelope.client_start_time);

                        Arc::clone(&host.sessions)
                    };

                    stream::iter_ok(envelope.messages)
                        .for_each(move |message| {
                            match message {
                                Message::Data {
                                    plugin,
                                    session_id,
                                    session_seq,
                                    body,
                                    fqdn,
                                    ..
                                } => Either::A(data_handler(
                                    Arc::clone(&sessions),
                                    client.clone(),
                                    AgentData {
                                        fqdn,
                                        plugin,
                                        session_id,
                                        session_seq,
                                        body,
                                    },
                                )),
                                Message::SessionCreateRequest { plugin, fqdn } => {
                                    Either::B(session_create_req_handler(
                                        Arc::clone(&sessions),
                                        client.clone(),
                                        fqdn,
                                        plugin,
                                    ))
                                }
                            }
                            .map_err(warp::reject::custom)
                            .map(|_| ())
                        })
                        .map(|_| {
                            warp::reply::with_status(
                                warp::reply(),
                                warp::http::StatusCode::ACCEPTED,
                            )
                        })
                },
            );

        let hosts = warp::any().map(move || Arc::clone(&hosts_state3));

        let sender = warp::get2()
            .and(warp::header::<String>("x-ssl-client-name").map(Fqdn))
            .and(warp::query::<GetArgs>())
            .and(hosts)
            .and_then(move |fqdn, args: GetArgs, hosts: SharedHosts| {
                // If we are not dealing with the same agent anymore, remove the host and put a new one in.
                if host::is_stale(&mut hosts.lock(), &fqdn, &args.client_start_time) {
                    let mut hosts = hosts.lock();

                    hosts.remove(&fqdn);

                    log::info!(
                        "Terminating all sessions on {:?} because start time has changed",
                        fqdn
                    );

                    host::get_or_insert(&mut hosts, fqdn.clone(), args.client_start_time.clone());

                    return Either::A(future::ok(ManagerMessages {
                        messages: vec![ManagerMessage::SessionTerminateAll { fqdn: fqdn.clone() }],
                    }));
                }

                let (sessions, queue) = {
                    let mut hosts = hosts.lock();

                    let host = host::get_or_insert(
                        &mut hosts,
                        fqdn.clone(),
                        args.client_start_time.clone(),
                    );

                    (Arc::clone(&host.sessions), Arc::clone(&host.queue))
                };

                let fut = flush_queue::flush(queue, Duration::from_secs(30))
                    .and_then(|xs| -> Result<Vec<ManagerMessage>, failure::Error> {
                        xs.into_iter()
                            .map(|x| serde_json::from_slice(&x).map_err(failure::Error::from))
                            .collect()
                    })
                    .map(move |mut xs| {
                        xs.retain(|x| session::is_session_valid(x, &sessions.lock()));

                        xs
                    })
                    .map(move |xs| {
                        let envelope = ManagerMessages { messages: xs };

                        log::debug!(
                            "MessageView.get: responding to {:?} with {:?} messages ({:?})",
                            fqdn,
                            envelope.messages.len(),
                            args.client_start_time
                        );

                        envelope
                    })
                    .map_err(warp::reject::custom);

                Either::B(fut)
            })
            .map(|envelope| warp::reply::json(&envelope));

        let log = warp::log("iml_agent_comms::api");

        let routes = warp::path("message").and(receiver.or(sender).with(log));

        let addr = iml_manager_env::get_http_agent2_addr();

        log::info!("Starting iml-agent-comms on {:?}", addr);

        let (_, fut) = warp::serve(routes).bind_with_graceful_shutdown(addr, rx);

        fut
    }));
}
