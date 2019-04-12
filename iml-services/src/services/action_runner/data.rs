// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::services::action_runner::error::ActionRunnerError;
use futures::{
    future::{loop_fn, Loop},
    sync::oneshot,
};
use iml_wire_types::{Action, ActionId, Fqdn, Id, ManagerMessage, PluginName};
use parking_lot::Mutex;
use std::{collections::HashMap, sync::Arc, time::Duration};
use tokio::prelude::*;
use tokio_timer::{clock, Delay};

pub type Shared<T> = Arc<Mutex<T>>;
pub type Sessions = HashMap<Fqdn, Id>;
pub type Rpcs = HashMap<ActionId, ActionInFlight>;
pub type SessionToRpcs = HashMap<Id, Rpcs>;

type Sender = oneshot::Sender<Result<serde_json::Value, String>>;

pub struct ActionInFlight {
    tx: Sender,
    pub action: Action,
}

impl ActionInFlight {
    pub fn new(action: Action, tx: Sender) -> Self {
        ActionInFlight { action, tx }
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
pub fn await_session(
    fqdn: Fqdn,
    sessions: Shared<Sessions>,
    timeout: Duration,
) -> impl Future<Item = Id, Error = ActionRunnerError> {
    let until = clock::now() + timeout;

    loop_fn(
        sessions,
        move |sessions| -> Box<
            Future<Item = Loop<Id, Shared<Sessions>>, Error = ActionRunnerError> + Send,
        > {
            if clock::now() >= until {
                log::info!(
                    "Could not find a session for {} after {:?} seconds",
                    fqdn,
                    timeout.as_secs()
                );

                return Box::new(future::err(ActionRunnerError::AwaitSession(fqdn.clone())));
            }

            match Arc::clone(&sessions).lock().get(&fqdn) {
                Some(id) => Box::new(future::ok(Loop::Break(id.clone()))),
                None => {
                    let when = clock::now() + Duration::from_millis(500);

                    Box::new(
                        Delay::new(when)
                            .from_err()
                            .map(move |_| Loop::Continue(sessions)),
                    )
                }
            }
        },
    )
}

pub fn insert_action_in_flight(
    id: Id,
    action_id: ActionId,
    action: ActionInFlight,
    session_to_rpcs: &mut SessionToRpcs,
) {
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
    session_to_rpcs
        .get_mut(id)
        .and_then(|rpcs| rpcs.remove(action_id))
}

pub fn create_data_message(
    session_id: Id,
    fqdn: Fqdn,
    body: impl Into<serde_json::Value>,
) -> ManagerMessage {
    ManagerMessage::Data {
        session_id,
        fqdn,
        plugin: PluginName("action_runner".to_string()),
        body: body.into(),
    }
}

#[cfg(test)]
mod tests {
    use super::{await_session, get_action_in_flight, insert_action_in_flight, ActionInFlight};
    use crate::services::action_runner::error::ActionRunnerError;
    use futures::sync::oneshot;
    use iml_wire_types::{Action, ActionId, Fqdn, Id};
    use parking_lot::Mutex;
    use std::collections::HashMap;
    use std::sync::Arc;
    use std::time::{Duration, Instant};
    use tokio::runtime;
    use tokio_timer::clock::{Clock, Now};

    struct MockNow(Instant);

    impl Now for MockNow {
        fn now(&self) -> Instant {
            self.0
        }
    }

    #[test]
    fn test_await_session_will_error_after_timeout() {
        let when = Instant::now() + Duration::from_secs(30);
        let clock = Clock::new_with_now(MockNow(when));

        let sessions = Arc::new(Mutex::new(HashMap::new()));

        let fut = await_session(Fqdn("host1".to_string()), sessions, Duration::from_secs(25));

        let actual = runtime::Builder::new()
            .clock(clock)
            .build()
            .unwrap()
            .block_on_all(fut);

        match actual {
            Ok(_) => panic!("await_session should have returned an error"),
            Err(ActionRunnerError::AwaitSession(fqdn)) => {
                assert_eq!(fqdn, Fqdn("host1".to_string()))
            }
            _ => panic!(
                "await_session should have returned a AwaitSession error, got a different one"
            ),
        }
    }

    #[test]
    fn test_await_session_will_return_id() {
        let when = Instant::now() + Duration::from_secs(25);
        let clock = Clock::new_with_now(MockNow(when));

        let fqdn = Fqdn("host1".to_string());
        let id = Id("eee-weww".to_string());

        let hm = vec![(fqdn, id.clone())].into_iter().collect();
        let sessions = Arc::new(Mutex::new(hm));

        let fut = await_session(
            Fqdn("host1".to_string()),
            Arc::clone(&sessions),
            Duration::from_secs(30),
        );

        let actual = runtime::Builder::new()
            .clock(clock)
            .build()
            .unwrap()
            .block_on_all(fut)
            .unwrap();

        assert_eq!(id, actual);

        assert!(sessions.try_lock().is_some());
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
