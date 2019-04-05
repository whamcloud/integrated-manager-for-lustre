// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::services::action_runner::error::ActionRunnerError;
use futures::{future::{loop_fn, Loop}, sync::oneshot};
use iml_wire_types::{Action, ActionId, ActionName, Fqdn, Id};
use parking_lot::Mutex;
use std::{collections::HashMap, sync::Arc, time::Duration};
use tokio::{prelude::*};
use tokio_timer::{clock, Delay};

pub type Shared<T> = Arc<Mutex<T>>;
pub type Sessions = HashMap<Fqdn, Id>;
pub type Rpcs<'a> = HashMap<ActionId, ActionInFlight>;
pub type SessionToRpcs<'a> = HashMap<Id, Rpcs<'a>>;

type Sender = oneshot::Sender<Result<serde_json::Value, String>>;

pub struct ActionInFlight {
    tx: Sender,
    pub action: Action,
}

impl ActionInFlight {
    pub fn new(action: impl Into<Action>, tx: Sender) -> Self {
        ActionInFlight {
            action: action.into(),
            tx,
        }
    }
    pub fn complete(
        self,
        x: Result<serde_json::Value, String>,
    ) -> Result<(), Result<serde_json::Value, String>> {
        self.tx.send(x)
    }
}

#[derive(serde::Deserialize, Debug)]
pub struct ManagerCommand {
    pub fqdn: Fqdn,
    pub action: ActionName,
    pub action_id: ActionId,
    pub args: Vec<String>,
}

impl From<ManagerCommand> for Action {
    fn from(m_cmd: ManagerCommand) -> Self {
        Action::ActionStart {
            action: m_cmd.action,
            args: m_cmd.args.into(),
            id: m_cmd.action_id,
        }
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

pub fn insert_action_in_flight<'a>(
    id: Id,
    action_id: ActionId,
    action: ActionInFlight,
    session_to_rpcs: Shared<SessionToRpcs<'a>>,
) {
    let mut session_to_rpcs = session_to_rpcs.lock();

    let rpcs = session_to_rpcs.entry(id).or_insert_with(|| HashMap::new());

    rpcs.insert(action_id, action);
}

#[cfg(test)]
mod tests {
    use super::await_session;
    use crate::services::action_runner::error::ActionRunnerError;
    use iml_wire_types::{Fqdn, Id};
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
}
