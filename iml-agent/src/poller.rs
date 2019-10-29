// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    daemon_plugins::OutputValue,
    http_comms::{
        agent_client::AgentClient,
        session::{SessionInfo, Sessions, State},
    },
};
use futures01::{future, Future, Stream};
use iml_wire_types::PluginName;
use std::time::{Duration, Instant};
use tracing::{error, info, trace};

fn send_if_data(
    agent_client: AgentClient,
) -> impl FnOnce(
    Option<(SessionInfo, OutputValue)>,
) -> Box<dyn Future<Item = (), Error = ImlAgentError> + Send> {
    move |x| match x {
        Some((info, output)) => Box::new(agent_client.send_data(info, output)),
        None => Box::new(future::ok(())),
    }
}

/// Given a `Session` wrapped in some `State`
/// this function will handle the state and move it to it's next state.
///
fn handle_state(
    state: &State,
    agent_client: AgentClient,
    mut sessions: Sessions,
    name: PluginName,
    now: Instant,
) -> Box<dyn Future<Item = (), Error = ImlAgentError> + Send> {
    trace!("handling state for {:?}: {:?}, ", name, state);

    match state {
        State::Active(a) if a.instant <= now => Box::new(
            a.session
                .poll()
                .and_then(send_if_data(agent_client.clone()))
                .then(move |r| match r {
                    Ok(_) => {
                        sessions.reset_active(&name);
                        Ok(())
                    }
                    Err(_) => sessions.terminate_session(&name),
                }),
        ),
        _ => Box::new(future::ok(())),
    }
}

/// Given some `Sessions`, this fn will poll them once per second.
///
/// A `Session` or other `State` will only be handled if their internal timers have passed the tick of this
/// internal interval `Stream`.
pub fn create_poller(
    agent_client: AgentClient,
    sessions: Sessions,
) -> impl Future<Item = (), Error = ImlAgentError> + 'static {
    tokio::timer::Interval::new_interval(Duration::from_secs(1))
        .from_err()
        .for_each(move |now| {
            trace!("interval triggered for {:?}", now);

            for (name, state) in sessions.clone().write().iter_mut() {
                match state {
                    State::Empty(wait) if *wait <= now => {
                        state.convert_to_pending();

                        let mut sessions = sessions.clone();
                        let name = name.clone();

                        info!("sending session create request for {}", name);

                        let fut = agent_client.create_session(name.clone()).map_err(move |e| {
                            info!("session create request for {} failed: {:?}", name, e);
                            sessions.reset_empty(&name)
                        });

                        tokio::spawn(fut);
                    }
                    _ => (),
                };
            }

            for (name, state) in sessions.clone().read().iter() {
                let fut = handle_state(
                    state,
                    agent_client.clone(),
                    sessions.clone(),
                    name.clone(),
                    now,
                );

                tokio::spawn(fut.map_err(|e| {
                    error!("{}", e);
                }));
            }

            Ok(())
        })
}
