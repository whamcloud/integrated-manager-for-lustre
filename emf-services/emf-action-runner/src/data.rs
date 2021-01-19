// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{error::ActionRunnerError, Sender, Sessions, Shared};
use emf_wire_types::{Action, ActionId, Fqdn, Id, ManagerMessage, PluginName};
use std::{collections::HashMap, convert::TryInto, sync::Arc, time::Duration};
use tokio::time::{delay_until, Instant};

pub type Rpcs = HashMap<ActionId, ActionInFlight>;
pub type SessionToRpcs = HashMap<Id, Rpcs>;

pub struct ActionInFlight {
    tx: Sender,
    pub action: Action,
}

impl ActionInFlight {
    pub fn new(action: Action, tx: Sender) -> Self {
        Self { action, tx }
    }
    pub fn complete(
        self,
        x: Result<serde_json::Value, String>,
    ) -> Result<(), Result<serde_json::Value, String>> {
        self.tx.send(x)
    }
}

/// Waits the given duration for a session matching the
/// `Fqdn` to appear. If a session appears a clone of `Id` is
/// returned.
///
/// If a session does not appear within the duration an Error is raised.
pub async fn await_session(
    fqdn: Fqdn,
    sessions: Shared<Sessions>,
    timeout: Duration,
) -> Result<Id, ActionRunnerError> {
    let until = Instant::now() + timeout;

    loop {
        if Instant::now() >= until {
            tracing::info!(
                "Could not find a session for {} after {:?} seconds",
                fqdn,
                timeout.as_secs()
            );

            return Err(ActionRunnerError::AwaitSession(fqdn.clone()));
        }

        if let Some(id) = sessions.lock().await.get(&fqdn) {
            return Ok(id.clone());
        }

        let when = Instant::now() + Duration::from_millis(500);

        delay_until(when).await;
    }
}

///  Tries to get the current session for a `Fqdn`.
pub(crate) async fn get_session(
    fqdn: Fqdn,
    sessions: Shared<Sessions>,
) -> Result<Option<Id>, ActionRunnerError> {
    let lock = { sessions.lock().await };
    let session = lock.get(&fqdn);

    Ok(session.cloned())
}

/// Waits `wait_secs` for a new session to appear that is different from the one provided.
///
/// If a new session does not appear within `wait_secs` an Error is raised.
pub(crate) async fn await_next_session(
    fqdn: Fqdn,
    last_session: Id,
    wait_secs: u32,
    sessions: Shared<Sessions>,
) -> Result<Id, ActionRunnerError> {
    for _ in 0..wait_secs {
        let session =
            await_session(fqdn.clone(), Arc::clone(&sessions), Duration::from_secs(30)).await?;

        if last_session != session {
            return Ok(session);
        }

        let when = Instant::now() + Duration::from_secs(1);

        delay_until(when).await;
    }

    tracing::warn!("No new session after {} seconds", wait_secs);

    Err(ActionRunnerError::AwaitSession(fqdn.clone()))
}

pub fn insert_action_in_flight(
    id: Id,
    action_id: ActionId,
    action: ActionInFlight,
    session_to_rpcs: &mut SessionToRpcs,
) {
    tracing::debug!(
        "Inserting new ActionInFlight with id {:?} and action_id {:?}",
        id,
        action_id
    );

    let rpcs = session_to_rpcs.entry(id).or_insert_with(HashMap::new);

    rpcs.insert(action_id, action);
}

pub fn get_action_in_flight<'a>(
    id: &Id,
    action_id: &ActionId,
    session_to_rpcs: &'a SessionToRpcs,
) -> Option<&'a ActionInFlight> {
    session_to_rpcs.get(id).and_then(|rpcs| rpcs.get(action_id))
}

pub fn has_action_in_flight(
    id: &Id,
    action_id: &ActionId,
    session_to_rpcs: &SessionToRpcs,
) -> bool {
    session_to_rpcs
        .get(id)
        .and_then(|rpcs| rpcs.get(action_id))
        .is_some()
}

pub fn remove_action_in_flight<'a>(
    id: &Id,
    action_id: &ActionId,
    session_to_rpcs: &'a mut SessionToRpcs,
) -> Option<ActionInFlight> {
    tracing::debug!(
        "Removing ActionInFlight with id {:?} and action_id {:?}",
        id,
        action_id
    );

    session_to_rpcs
        .get_mut(id)
        .and_then(|rpcs| rpcs.remove(action_id))
}

pub fn create_data_message(
    session_id: Id,
    fqdn: Fqdn,
    body: impl TryInto<serde_json::Value, Error = serde_json::Error>,
) -> ManagerMessage {
    ManagerMessage::Data {
        session_id,
        fqdn,
        plugin: PluginName("action_runner".to_string()),
        body: body.try_into().unwrap(),
    }
}

#[cfg(test)]
mod tests {
    use super::{await_session, get_action_in_flight, insert_action_in_flight, ActionInFlight};
    use crate::error::ActionRunnerError;
    use emf_wire_types::{Action, ActionId, Fqdn, Id};
    use futures::{channel::oneshot, lock::Mutex};
    use std::{collections::HashMap, sync::Arc};
    use tokio::time::{self, Duration};
    use tokio_test::{assert_pending, assert_ready_err, task};

    #[tokio::test]
    async fn test_await_session_will_error_after_timeout2() {
        time::pause();

        let sessions = Arc::new(Mutex::new(HashMap::new()));

        let mut task = task::spawn(await_session(
            Fqdn("host1".to_string()),
            sessions,
            Duration::from_secs(25),
        ));

        assert_pending!(task.poll());

        time::advance(Duration::from_secs(26)).await;

        assert_ready_err!(task.poll());
    }

    #[tokio::test]
    async fn test_await_session_will_return_id() -> Result<(), ActionRunnerError> {
        let fqdn = Fqdn("host1".to_string());
        let id = Id("eee-weww".to_string());

        let hm = vec![(fqdn, id.clone())].into_iter().collect();
        let sessions = Arc::new(Mutex::new(hm));

        let actual = await_session(
            Fqdn("host1".to_string()),
            Arc::clone(&sessions),
            Duration::from_secs(30),
        )
        .await?;

        assert_eq!(id, actual);

        assert!(sessions.try_lock().is_some());

        Ok(())
    }

    #[test]
    fn test_insert_action_in_flight() {
        let id = Id("eee-weww".to_string());
        let action = Action::ActionCancel {
            id: ActionId("1234".to_string()),
        };
        let mut session_to_rpcs = HashMap::new();

        let (tx, _) = oneshot::channel();

        let action_id = action.get_id().clone();

        let action_in_flight = ActionInFlight::new(action, tx);

        insert_action_in_flight(id, action_id, action_in_flight, &mut session_to_rpcs);

        assert_eq!(session_to_rpcs.len(), 1);
    }

    #[test]
    fn test_get_action_in_flight() {
        let id = Id("eee-weww".to_string());
        let action = Action::ActionCancel {
            id: ActionId("1234".to_string()),
        };

        let (tx, _) = oneshot::channel();

        let action_id = action.get_id().clone();

        let action_in_flight = ActionInFlight::new(action.clone(), tx);

        let rpcs = vec![(action_id.clone(), action_in_flight)]
            .into_iter()
            .collect();

        let session_to_rpcs = vec![(id.clone(), rpcs)].into_iter().collect();

        let actual = get_action_in_flight(&id, &action_id, &session_to_rpcs).unwrap();

        assert_eq!(actual.action, action);
    }
}
