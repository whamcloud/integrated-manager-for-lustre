// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    http_comms::{
        agent_client::AgentClient,
        session::{Sessions, State},
    },
};
use futures::{
    future::{self, Either},
    Future, FutureExt, TryFutureExt,
};
use iml_wire_types::PluginName;
use std::time::{Duration, Instant};
use tokio::timer::Interval;
use tracing::error;

/// Given a `Session` wrapped in some `State`
/// this function will handle the state and move it to it's next state.
///
fn handle_state(
    state: &State,
    agent_client: AgentClient,
    mut sessions: Sessions,
    name: PluginName,
    now: Instant,
) -> impl Future<Output = Result<(), ImlAgentError>> {
    tracing::trace!("handling state for {:?}: {:?}, ", name, state);

    match state {
        State::Active(a) if a.instant <= now => Either::Left(
            a.session
                .poll()
                .and_then(move |x| {
                    async move {
                        if let Some((info, output)) = x {
                            agent_client.send_data(info, output).await?;
                        }

                        Ok(())
                    }
                })
                .then(move |r| match r {
                    Ok(_) => {
                        sessions.reset_active(&name);
                        future::ok(())
                    }
                    Err(_) => future::ready(sessions.terminate_session(&name)),
                }),
        ),
        _ => Either::Right(future::ok(())),
    }
}

/// Given some `Sessions`, this fn will poll them once per second.
///
/// A `Session` or other `State` will only be handled if their internal timers have passed the tick of this
/// internal interval `Stream`.
pub async fn create_poller(
    agent_client: AgentClient,
    sessions: Sessions,
) -> Result<(), ImlAgentError> {
    let mut s = Interval::new_interval(Duration::from_secs(1));

    while let Some(now) = s.next().await {
        tracing::trace!("interval triggered for {:?}", now);

        for (name, state) in sessions.clone().write().iter_mut() {
            match state {
                State::Empty(wait) if *wait <= now => {
                    state.convert_to_pending();

                    let mut sessions = sessions.clone();
                    let name = name.clone();

                    tracing::info!("sending session create request for {}", name);

                    let fut = agent_client.create_session(name.clone()).map_err(move |e| {
                        tracing::info!("session create request for {} failed: {:?}", name, e);
                        sessions.reset_empty(&name)
                    });

                    tokio::spawn(async {
                        fut.await;
                    });
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

            tokio::spawn(async move {
                fut.await.map_err(|e| {
                    error!("{}", e);
                });
            });
        }
    }

    Ok(())
}
