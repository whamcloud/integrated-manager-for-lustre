// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::{
    command_plan::OutputWriter,
    input_document::{client_mount, filesystem, host, lnet, mdt, mgt, mgt_mdt},
    state_schema::Input,
    Error,
};
use emf_postgres::PgPool;
use emf_ssh::{SshChannelExt as _, SshHandleExt};
use emf_tracing::tracing;
use emf_wire_types::{Action, ActionId, ActionName, AgentResult, Fqdn};
use futures::{FutureExt, TryFutureExt};
use once_cell::sync::Lazy;
use std::{collections::HashMap, sync::Arc, time::Duration};
use tokio::{
    io::{copy, AsyncWriteExt},
    sync::{
        oneshot::{self, Receiver, Sender},
        Mutex,
    },
    time::{self, timeout_at, Instant},
};
use uuid::Uuid;

pub type OutgoingHostQueues = Arc<Mutex<HashMap<Fqdn, Vec<Action>>>>;

pub static OUTGOING_HOST_QUEUES: Lazy<OutgoingHostQueues> =
    Lazy::new(|| Arc::new(Mutex::new(HashMap::new())));

pub type IncomingHostQueues =
    Arc<Mutex<HashMap<Fqdn, HashMap<ActionId, oneshot::Sender<AgentResult>>>>>;

pub static INCOMING_HOST_QUEUES: Lazy<IncomingHostQueues> =
    Lazy::new(|| Arc::new(Mutex::new(HashMap::new())));

pub(crate) async fn invoke_remote(
    fqdn: Fqdn,
    action: ActionName,
    args: serde_json::value::Value,
) -> (Sender<()>, Receiver<AgentResult>) {
    let action_id = ActionId(Uuid::new_v4().to_string());

    let (tx, rx) = oneshot::channel();

    let mut qs = INCOMING_HOST_QUEUES.lock().await;

    let q = qs.entry(fqdn.clone()).or_insert(HashMap::new());
    q.insert(action_id.clone(), tx);

    let mut qs = OUTGOING_HOST_QUEUES.lock().await;

    let q = qs.entry(fqdn.clone()).or_insert(vec![]);

    q.push(Action::ActionStart {
        action,
        id: action_id.clone(),
        args,
    });

    let (tx, rx2) = oneshot::channel();

    let fqdn = fqdn.clone();
    tokio::spawn(async move {
        if rx2.await.is_err() {
            return;
        };

        let mut qs = OUTGOING_HOST_QUEUES.lock().await;

        let q = qs.entry(fqdn.clone()).or_insert(vec![]);
        q.push(Action::ActionCancel { id: action_id });
    });

    (tx, rx)
}

pub(crate) async fn invoke<'a>(
    pg_pool: PgPool,
    mut stdout_writer: OutputWriter,
    mut stderr_writer: OutputWriter,
    input: &'a Input,
) -> Result<(), Error> {
    match input {
        Input::Host(x) => match x {
            host::Input::SshCommand(x) => {
                let opts = &x.ssh_opts;

                let mut session = emf_ssh::connect(
                    &x.host,
                    opts.port,
                    &opts.user,
                    (&opts.auth_opts).into(),
                    opts.proxy_opts.as_ref().map(From::from),
                )
                .await?;

                let channel = session
                    .channel_open_session()
                    .err_into::<emf_ssh::Error>()
                    .await?;

                let mut child = channel.spawn(&x.run).await?;

                if let Some(mut x) = child.stdout.take() {
                    tokio::spawn(
                        async move { copy(&mut x, &mut stdout_writer).await }
                            .map_ok(drop)
                            .map_err(|e| tracing::warn!("Could not copy stdout {:?}", e)),
                    );
                }

                if let Some(mut x) = child.stderr.take() {
                    tokio::spawn(
                        async move { copy(&mut x, &mut stderr_writer).await }
                            .map_ok(drop)
                            .map_err(|e| tracing::warn!("Could not copy stderr {:?}", e)),
                    );
                }

                let code = child.wait().await?;

                if code != 0 {
                    return Err(Error::SshError(emf_ssh::Error::BadStatus(code)));
                }
            }
            host::Input::SetupPlanesSsh(host::SetupPlanesSsh {
                host,
                cp_addr,
                ssh_opts,
            }) => {
                let mut session = emf_ssh::connect(
                    &host,
                    ssh_opts.port,
                    &ssh_opts.user,
                    (&ssh_opts.auth_opts).into(),
                    ssh_opts.proxy_opts.as_ref().map(From::from),
                )
                .await?;

                let overrides = format!("CP_ADDR={}\nMGMT_ADDR={}", cp_addr, host);

                session
                    .stream_file(overrides.as_bytes(), "/etc/emf/overrides.conf")
                    .await?;
            }
            host::Input::CreateFileSsh(host::CreateFileSsh {
                host,
                contents,
                ssh_opts,
                path,
            }) => {
                let mut session = emf_ssh::connect(
                    &host,
                    ssh_opts.port,
                    &ssh_opts.user,
                    (&ssh_opts.auth_opts).into(),
                    ssh_opts.proxy_opts.as_ref().map(From::from),
                )
                .await?;

                session.stream_file(contents.as_bytes(), path).await?;
            }
            host::Input::SyncFileSsh(host::SyncFileSsh {
                host,
                from,
                ssh_opts,
            }) => {
                let mut session = emf_ssh::connect(
                    &host,
                    ssh_opts.port,
                    &ssh_opts.user,
                    (&ssh_opts.auth_opts).into(),
                    ssh_opts.proxy_opts.as_ref().map(From::from),
                )
                .await?;

                session.push_file(&from, &from).await?;
            }
            host::Input::IsAvailable(host::IsAvailable { fqdn, timeout }) => {
                let timeout = timeout.unwrap_or_else(|| Duration::from_secs(30));

                let mut interval = time::interval(Duration::from_millis(500));

                let f = async {
                    loop {
                        interval.tick().await;

                        let x = sqlx::query!(
                            "SELECT id FROM host WHERE fqdn = $1 AND state = 'up'",
                            &fqdn
                        )
                        .fetch_optional(&pg_pool)
                        .await
                        .transpose();

                        match x {
                            Some(Ok(_)) => break,
                            _ => continue,
                        };
                    }
                };

                match timeout_at(Instant::now() + timeout, f).await {
                    Ok(_) => {
                        stdout_writer
                            .write_all(format!("FQDN: {} found in EMF database", fqdn).as_bytes())
                            .map_err(|e| tracing::warn!("Could not write stdout {:?}", e))
                            .map(drop)
                            .await;

                        stdout_writer
                            .flush()
                            .map_err(|e| tracing::warn!("Could not flush stdout {:?}", e))
                            .map(drop)
                            .await;
                    }
                    Err(_) => {
                        stderr_writer
                            .write_all(
                                format!(
                                    "FQDN: {} not found in EMF database after waiting {} seconds",
                                    fqdn,
                                    timeout.as_secs()
                                )
                                .as_bytes(),
                            )
                            .map_err(|e| tracing::warn!("Could not write stderr {:?}", e))
                            .map(drop)
                            .await;

                        stderr_writer
                            .flush()
                            .map_err(|e| tracing::warn!("Could not flush stderr {:?}", e))
                            .map(drop)
                            .await;
                    }
                };
            }
        },
        Input::Lnet(x) => match x {
            lnet::Input::Start(x) => {}
            lnet::Input::Stop(x) => {}
            lnet::Input::Load(x) => {}
            lnet::Input::Unload(x) => {}
            lnet::Input::Configure(x) => {}
            lnet::Input::Export(x) => {}
            lnet::Input::Unconfigure(x) => {}
            lnet::Input::Import(x) => {}
        },
        Input::ClientMount(x) => match x {
            client_mount::Input::Create(x) => {}
            client_mount::Input::Unmount(x) => {}
            client_mount::Input::Mount(x) => {}
        },
        Input::Mgt(x) => match x {
            mgt::Input::Format(x) => {}
            mgt::Input::Mount(x) => {}
            mgt::Input::Unmount(x) => {}
        },
        Input::MgtMdt(x) => match x {
            mgt_mdt::Input::Format(x) => {}
            mgt_mdt::Input::Mount(x) => {}
            mgt_mdt::Input::Unmount(x) => {}
        },
        Input::Mdt(x) => match x {
            mdt::Input::Format(x) => {}
            mdt::Input::Mount(x) => {}
            mdt::Input::Unmount(x) => {}
        },
        Input::Ost(x) => match x {
            crate::input_document::ost::Input::Format(x) => {}
            crate::input_document::ost::Input::Mount(x) => {}
            crate::input_document::ost::Input::Unmount(x) => {}
        },
        Input::Filesystem(x) => match x {
            filesystem::Input::Start(x) => {}
            filesystem::Input::Stop(x) => {}
            filesystem::Input::Create(x) => {}
        },
    };

    Ok(())
}
