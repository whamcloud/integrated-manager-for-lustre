// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    daemon_plugins::{get_plugin, DaemonPlugins, OutputValue},
    http_comms::{
        agent_client::AgentClient,
        session::{Session, SessionInfo, Sessions, State},
    },
};
use futures::{
    future::{self, loop_fn, Future, Loop},
    stream::{self, Stream},
};
use iml_wire_types::ManagerMessage;
use std::time::{Duration, Instant};
use tokio::timer::Delay;

fn send_if_data(
    agent_client: AgentClient,
) -> impl FnOnce(
    Option<(SessionInfo, OutputValue)>,
) -> Box<Future<Item = (), Error = ImlAgentError> + Send> {
    move |x| match x {
        Some((info, output)) => Box::new(agent_client.send_data(info, output)),
        None => Box::new(future::ok(())),
    }
}

type LoopState = Loop<(), (AgentClient, Sessions, std::sync::Arc<DaemonPlugins>)>;

/// Continually polls the manager for any incoming commands using a tail-recursive loop.
pub fn create_reader(
    sessions: Sessions,
    agent_client: AgentClient,
    registry: DaemonPlugins,
) -> impl Future<Item = (), Error = ImlAgentError> {
    loop_fn(
        (agent_client, sessions, std::sync::Arc::new(registry)),
        move |(agent_client, mut sessions, registry)| {
            let mut sessions2 = sessions.clone();
            let agent_client2 = agent_client.clone();
            let registry2 = registry.clone();

            agent_client
                .clone()
                .get()
                .map(|x| x.messages)
                .into_stream()
                .map(stream::iter_ok)
                .flatten()
                .and_then(move |x| {
                    log::debug!("Reader: {:?}", x);

                    match x {
                        ManagerMessage::SessionCreateResponse {
                            plugin, session_id, ..
                        } => {
                            let plugin_instance = get_plugin(&plugin, &registry2)?;

                            let s = Session::new(plugin.clone(), session_id, plugin_instance);

                            let mut sessions3 = sessions2.clone();
                            let plugin2 = plugin.clone();

                            tokio::spawn(
                                s.start()
                                    .and_then(send_if_data(agent_client2.clone()))
                                    .or_else(move |e| {
                                        log::warn!("Error during session start {:?}", e);
                                        sessions3.terminate_session(&plugin2)
                                    })
                                    .map_err(|e| {
                                        log::error!("Got an error adding session {:?}", e)
                                    }),
                            );

                            sessions2.insert_session(plugin, s)
                        }
                        ManagerMessage::Data {
                            plugin,
                            session_id,
                            body,
                            ..
                        } => match sessions2.lock().get_mut(&plugin) {
                            Some(State::Active(s)) => {
                                let agent_client3 = agent_client2.clone();

                                let fut = s
                                    .session
                                    .message(body)
                                    .and_then(move |(info, x)| agent_client3.send_data(info, x))
                                    .map_err(|e| log::error!("{}", e));

                                tokio::spawn(fut);

                                Ok(())
                            }
                            _ => {
                                log::warn!(
                                    "Received a message for unknown session {:?}/{:?}",
                                    plugin,
                                    session_id
                                );
                                Ok(())
                            }
                        },
                        ManagerMessage::SessionTerminate {
                            plugin,
                            session_id: _,
                            ..
                        } => sessions2.terminate_session(&plugin),
                        ManagerMessage::SessionTerminateAll { .. } => {
                            sessions2.terminate_all_sessions()
                        }
                    }
                })
                .collect()
                .then(
                    |r| -> Box<Future<Item = LoopState, Error = ImlAgentError> + Send> {
                        match r {
                            Ok(_) => Box::new(future::ok(Loop::Continue((
                                agent_client,
                                sessions,
                                registry,
                            )))),
                            Err(ImlAgentError::Reqwest(e)) => {
                                log::warn!(
                                    "Got a manager read Error {:?}. Will retry in 5 seconds.",
                                    e
                                );

                                if let Err(e) = sessions.terminate_all_sessions() {
                                    return Box::new(future::err(e));
                                };

                                let when = Instant::now() + Duration::from_secs(5);
                                Box::new(
                                    Delay::new(when).from_err().map(|_| {
                                        Loop::Continue((agent_client, sessions, registry))
                                    }),
                                )
                            }
                            Err(e) => Box::new(future::err(e)),
                        }
                    },
                )
        },
    )
}
