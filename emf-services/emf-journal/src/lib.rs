// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_postgres::alert;
use emf_wire_types::{AlertRecordType, AlertSeverity, ComponentType, MessageClass};
use future::BoxFuture;
use futures::{future, FutureExt, TryFutureExt};
use lazy_static::lazy_static;
use regex::Regex;
use sqlx::postgres::PgPool;
use std::collections::HashMap;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum EmfJournalError {
    #[error(transparent)]
    SerdeJsonError(#[from] serde_json::Error),
    #[error(transparent)]
    SqlxCoreError(#[from] sqlx::error::Error),
    #[error(transparent)]
    TryFromIntError(#[from] std::num::TryFromIntError),
}

lazy_static! {
    static ref LUSTRE_ERROR_TS: Regex = Regex::new(r"^\[\d+\.\d+\] LustreError:").unwrap();
    static ref LUSTRE_TS: Regex = Regex::new(r"^\[\d+\.\d+\] Lustre:").unwrap();
    static ref LUSTRE_ERROR: Regex = Regex::new(r"^LustreError:").unwrap();
    static ref LUSTRE: Regex = Regex::new(r"^Lustre:").unwrap();
}

type HandlerFut<'a> = BoxFuture<'a, Result<(), EmfJournalError>>;
type Handler = for<'a> fn(&'a PgPool, &'a str, i32) -> HandlerFut<'a>;

lazy_static! {
    static ref HANDLERS: HashMap<&'static str, Handler> = {
        let mut hm: HashMap<&'static str, Handler> = HashMap::new();

        hm.insert("Can't start acceptor on port", port_used_handler);
        hm.insert("Can't create socket:", port_used_handler);
        hm.insert(": connection from ", client_connection_handler);
        hm.insert(": select flavor ", server_security_flavor_handler);
        hm.insert(
            ": obd_export_evict_by_uuid()",
            admin_client_eviction_handler,
        );
        hm.insert(": evicting client at ", client_eviction_handler);

        hm
    };
}

pub fn get_message_class(message: &str) -> MessageClass {
    if LUSTRE_ERROR_TS.is_match(message) || LUSTRE_ERROR.is_match(message) {
        MessageClass::LustreError
    } else if LUSTRE_TS.is_match(message) || LUSTRE.is_match(message) {
        MessageClass::Lustre
    } else {
        MessageClass::Normal
    }
}

fn port_used_handler<'a>(
    pool: &'a PgPool,
    _: &str,
    host_id: i32,
) -> BoxFuture<'a, Result<(), EmfJournalError>> {
    alert::raise(
        pool,
        AlertRecordType::SyslogEvent,
        "Lustre port already being used".into(),
        ComponentType::Host,
        None,
        AlertSeverity::ERROR,
        host_id,
    )
    .err_into()
    .boxed()
}

fn client_connection_handler<'a>(pool: &'a PgPool, msg: &str, host_id: i32) -> HandlerFut<'a> {
    if let Some((lustre_pid, msg)) = client_connection_parser(msg) {
        return alert::raise(
            pool,
            AlertRecordType::ClientConnectEvent,
            msg,
            ComponentType::Host,
            Some(lustre_pid),
            AlertSeverity::INFO,
            host_id,
        )
        .err_into()
        .boxed();
    };

    future::ok(()).boxed()
}

/// Parses a client connected to a target
fn client_connection_parser(msg: &str) -> Option<(i32, String)> {
    lazy_static! {
        static ref TARGET_END: Regex = Regex::new(r":\s+connection from").unwrap();
    }

    // get the client NID out of the string
    let nid_start = msg.find('@')? + 1;
    let nid_len = msg[nid_start..].find(' ')?;
    // and the UUID
    let uuid_start = msg.find(" from ")? + 6;
    let uuid_len = msg[uuid_start..].find('@')?;
    // and of course the target
    let target_end = TARGET_END.find(msg)?.start();
    let target_start = msg[0..target_end].rfind(' ')? + 1;

    let lustre_pid = msg[9..9 + msg[9..].find(':')?].parse::<i32>().ok()?;
    let msg = format!(
        "client {} from {} connected to target {}",
        &msg[uuid_start..uuid_start + uuid_len],
        &msg[nid_start..nid_start + nid_len],
        &msg[target_start..target_end],
    );

    Some((lustre_pid, msg))
}

fn server_security_flavor_parser(msg: &str) -> Option<(i32, String)> {
    // get the flavor out of the string
    let flavor_start = msg.rfind(' ')? + 1;
    let flavor = &msg[flavor_start..];
    let lustre_pid = msg[9..9 + msg[9..].find(':')?].parse::<i32>().ok()?;

    Some((lustre_pid, format!("with security flavor {}", flavor)))
}

fn server_security_flavor_handler<'a>(pool: &'a PgPool, msg: &str, _: i32) -> HandlerFut<'a> {
    let (lustre_pid, msg) = match server_security_flavor_parser(msg) {
        Some(x) => x,
        None => return future::ok(()).boxed(),
    };

    struct Row {
        id: i32,
        message: Option<String>,
    }

    async move {
        let row = sqlx::query_as!(
            Row,
            "SELECT id, message FROM alertstate WHERE lustre_pid = $1 ORDER BY id DESC LIMIT 1",
            Some(lustre_pid)
        )
        .fetch_optional(pool)
        .await?;

        let (id, msg) = match row {
            Some(Row {
                id,
                message: Some(message),
            }) => (id, format!("{} {}", message, msg)),
            Some(Row { message: None, .. }) | None => return Ok(()),
        };

        sqlx::query!(
            r#"
            UPDATE alertstate
            SET message = $1
            WHERE
                id = $2
        "#,
            msg,
            id
        )
        .execute(pool)
        .await?;

        Ok(())
    }
    .boxed()
}

fn admin_client_eviction_parser(msg: &str) -> Option<(i32, String)> {
    let uuid = get_item_after(msg, "evicting ")?;
    let x = format!("client {} evicted by the administrator", uuid);
    let lustre_pid = msg[9..9 + msg[9..].find(':')?].parse::<i32>().ok()?;

    Some((lustre_pid, x))
}

fn admin_client_eviction_handler<'a>(pool: &'a PgPool, msg: &str, host_id: i32) -> HandlerFut<'a> {
    if let Some((lustre_pid, msg)) = admin_client_eviction_parser(msg) {
        return alert::raise(
            pool,
            AlertRecordType::ClientConnectEvent,
            msg,
            ComponentType::Host,
            Some(lustre_pid),
            AlertSeverity::WARNING,
            host_id,
        )
        .err_into()
        .boxed();
    };

    future::ok(()).boxed()
}

fn client_eviction_parser(msg: &str) -> Option<(i32, String)> {
    let s = msg.find("### ")? + 4;
    let l = msg[s..].find(": evicting client at ")?;
    let reason = &msg[s..s + l];
    let client = get_item_after(msg, ": evicting client at ")?;
    let lustre_pid = get_item_after(msg, "pid: ")?.parse::<i32>().ok()?;

    Some((lustre_pid, format!("client {} evicted: {}", client, reason)))
}

fn client_eviction_handler<'a>(pool: &'a PgPool, msg: &str, host_id: i32) -> HandlerFut<'a> {
    if let Some((lustre_pid, msg)) = client_eviction_parser(msg) {
        return alert::raise(
            pool,
            AlertRecordType::ClientConnectEvent,
            msg,
            ComponentType::Host,
            Some(lustre_pid),
            AlertSeverity::WARNING,
            host_id,
        )
        .err_into()
        .boxed();
    };

    future::ok(()).boxed()
}

fn get_item_after<'a>(s: &'a str, after: &str) -> Option<&'a str> {
    let sub = s.find(after)? + after.len();
    let l = s[sub..].find(' ')?;

    Some(&s[sub..sub + l])
}

fn find_one_in_many<'a>(msg: &str, handlers: &'a HashMap<&str, Handler>) -> Option<&'a Handler> {
    handlers
        .iter()
        .find(|(k, _)| k.contains(msg))
        .map(|(_, v)| v)
}

pub async fn execute_handlers(
    msg: &str,
    host_id: i32,
    pool: &PgPool,
) -> Result<(), EmfJournalError> {
    let handler = match find_one_in_many(msg, &HANDLERS) {
        Some(h) => h,
        None => return Ok(()),
    };

    handler(pool, msg, host_id).await?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use insta::assert_debug_snapshot;

    #[test]
    fn test_get_message_class() {
        let tests = vec![
            (
                "[NOT A TIME STAMP ] Lustre: Lustre output here",
                MessageClass::Normal,
            ),
            ("Lustre: Lustre output here", MessageClass::Lustre),
            ("LustreError: Lustre output here", MessageClass::LustreError),
            (
                "[1234567A89] LustreError: Not A Time Stamp",
                MessageClass::Normal,
            ),
            (
                "[123456789.123456789A] LustreError: Not A Time Stamp",
                MessageClass::Normal,
            ),
            ("Nothing to see here", MessageClass::Normal),
        ];

        for (msg, expected) in tests {
            assert_eq!(get_message_class(msg), expected, "{}", msg);

            assert_eq!(
                get_message_class(&format!("[9830337.7944560] {}", msg)),
                expected,
                "[9830337.7944560] {} ",
                msg
            );
        }
    }

    #[test]
    fn test_client_connection_parser() {
        let inputs = vec![
                " Lustre: 5629:0:(ldlm_lib.c:877:target_handle_connect()) lustre-MDT0000: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994929 last 0",
                " Lustre: 27559:0:(ldlm_lib.c:871:target_handle_connect()) lustre-OST0001: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994930 last 0",
                " Lustre: 9150:0:(ldlm_lib.c:871:target_handle_connect()) lustre-OST0000: connection from 26959b68-1208-1fca-1f07-da2dc872c55f@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994930 last 0",
                " Lustre: 31793:0:(ldlm_lib.c:877:target_handle_connect()) MGS:            connection from e5232e74-1e61-fad1-b59b-6e4a7d674016@192.168.122.218@tcp t0 exp 0000000000000000 cur 1317994928 last 0",
        ];

        for input in inputs {
            assert_debug_snapshot!(client_connection_parser(input).unwrap());
        }
    }

    #[test]
    fn test_server_security_flavor_parser() {
        let inputs = vec![
                " Lustre: 5629:0:(sec.c:1474:sptlrpc_import_sec_adapt()) import lustre-MDT0000->NET_0x20000c0a87ada_UUID netid 20000: select flavor null",
                "Lustre: 20380:0:(sec.c:1474:sptlrpc_import_sec_adapt()) import MGC192.168.122.105@tcp->MGC192.168.122.105@tcp_0 netid 20000: select flavor null"
        ];

        for input in inputs {
            assert_debug_snapshot!(server_security_flavor_parser(input).unwrap());
        }
    }

    #[test]
    fn test_admin_client_eviction_parser() {
        let x = " Lustre: 2689:0:(genops.c:1379:obd_export_evict_by_uuid()) lustre-OST0001: evicting 26959b68-1208-1fca-1f07-da2dc872c55f at adminstrative request";

        assert_debug_snapshot!(admin_client_eviction_parser(x).unwrap());
    }

    #[test]
    fn test_client_eviction_parser() {
        let inputs = vec![
            " LustreError: 0:0:(ldlm_lockd.c:356:waiting_locks_callback()) ### lock callback timer expired after 101s: evicting client at 0@lo ns: mdt-ffff8801cd5be000 lock: ffff880126f8f480/0xe99a593b682aed45 lrc: 3/0,0 mode: PR/PR res: 8589935876/10593 bits 0x3 rrc: 2 type: IBT flags: 0x4000020 remote: 0xe99a593b682aecea expref: 14 pid: 3636 timeout: 4389324308'",
            " LustreError: 0:0:(ldlm_lockd.c:356:waiting_locks_callback()) ### lock callback timer expired after 151s: evicting client at 10.10.6.127@tcp ns: mdt-ffff880027554000 lock: ffff8800345b9480/0x7e9e6dc241f05651 lrc: 3/0,0 mode: PR/PR res: 8589935619/19678 bits 0x3 rrc: 2 type: IBT flags: 0x4000020 remote: 0xebc1380d8b532fd7 expref: 5104 pid: 23056 timeout: 4313115550"];

        for input in inputs {
            assert_debug_snapshot!(client_eviction_parser(input).unwrap());
        }
    }
}
