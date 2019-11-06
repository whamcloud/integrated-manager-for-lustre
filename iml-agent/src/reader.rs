// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::ImlAgentError,
    daemon_plugins::{get_plugin, DaemonPlugins},
    http_comms::{
        agent_client::AgentClient,
        session::{Session, Sessions},
    },
};
use futures::{FutureExt, TryFutureExt};
use iml_wire_types::ManagerMessage;
use std::time::{Duration, Instant};
use tokio::timer::delay;
use tracing::{error, warn};

async fn get_delivery(
    mut sessions: Sessions,
    agent_client: AgentClient,
    registry: &DaemonPlugins,
) -> Result<(), ImlAgentError> {
    let msgs = agent_client.clone().get().map_ok(|x| x.messages).await?;

    for x in msgs {
        let mut sessions2 = sessions.clone();
        let agent_client2 = agent_client.clone();

        tracing::debug!("--> Delivery from manager {:?}", x);

        match x {
            ManagerMessage::SessionCreateResponse {
                plugin, session_id, ..
            } => {
                let plugin_instance = get_plugin(&plugin, &registry)?;
                let mut s = Session::new(plugin.clone(), session_id, plugin_instance);
                let fut = s.start();

                sessions2.insert_session(plugin.clone(), s);

                let agent_client3 = agent_client2.clone();

                tokio::spawn(
                    async move {
                        if let Some((info, output)) = fut.await? {
                            agent_client3.send_data(info, output).await?;
                        }

                        Ok(())
                    }
                        .map(move |r: Result<(), ImlAgentError>| match r {
                            Ok(_) => (),
                            Err(e) => {
                                tracing::warn!("Error during session start {:?}", e);
                                sessions2.terminate_session(&plugin).unwrap_or_else(|e| {
                                    tracing::warn!("Error terminating session, {}", e)
                                });
                            }
                        }),
                );
            }
            ManagerMessage::Data {
                plugin,
                session_id,
                body,
                ..
            } => {
                let r = { sessions2.message(&plugin, body) };

                if let Some(fut) = r {
                    let agent_client3 = agent_client2.clone();

                    tokio::spawn(
                        async move {
                            let (info, x) = fut.await?;

                            agent_client3.send_data(info, x).await?;

                            Ok(())
                        }
                            .map_err(|e: ImlAgentError| error!("{}", e))
                            .map(drop),
                    );
                };
            }
            ManagerMessage::SessionTerminate {
                plugin,
                session_id: _,
                ..
            } => sessions.terminate_session(&plugin)?,
            ManagerMessage::SessionTerminateAll { .. } => sessions.terminate_all_sessions()?,
        }
    }

    Ok(())
}

/// Continually polls the manager for any incoming commands using a loop.
pub async fn create_reader(
    mut sessions: Sessions,
    agent_client: AgentClient,
    registry: DaemonPlugins,
) -> Result<(), ImlAgentError> {
    loop {
        match get_delivery(sessions.clone(), agent_client.clone(), &registry).await {
            Ok(_) => continue,
            Err(ImlAgentError::Reqwest(e)) => {
                warn!("Got a manager read Error {:?}. Will retry in 5 seconds.", e);

                if let Err(e) = sessions.terminate_all_sessions() {
                    return Err(e);
                };

                let when = Instant::now() + Duration::from_secs(5);
                delay(when).await;
            }
            Err(e) => return Err(e),
        }
    }
}
