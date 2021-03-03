// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use emf_ssh::{Output, SshChannelExt as _, SshHandleExt};
use emf_wire_types::{Action, ActionId, ActionName, AgentResult, Fqdn};
use futures::{stream, StreamExt, TryFutureExt, TryStreamExt};
use once_cell::sync::Lazy;
use std::{
    collections::{BTreeSet, HashMap},
    sync::Arc,
};
use tokio::sync::{
    oneshot::{self, Receiver, Sender},
    Mutex,
};
use uuid::Uuid;

use crate::{
    input_document::{client_mount, filesystem, host, lnet, mdt, mgt, mgt_mdt},
    state_schema::Input,
    Error,
};

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

pub fn parse_hosts(hosts: &[String]) -> Result<BTreeSet<String>, Error> {
    let parsed: Vec<BTreeSet<String>> = hosts
        .iter()
        .map(|x| hostlist_parser::parse(x).map_err(|x| x.map_range(|r| r.to_string())))
        .collect::<Result<_, _>>()?;

    let union = parsed
        .into_iter()
        .fold(BTreeSet::new(), |acc, h| acc.union(&h).cloned().collect());

    Ok(union)
}

pub(crate) async fn invoke<'a>(input: &'a Input) -> Result<(), Error> {
    match input {
        Input::Host(x) => match x {
            host::Input::SshCommand(x) => {
                let opts = &x.ssh_opts;

                let mut session =
                    emf_ssh::connect(&x.host, opts.port, &opts.user, (&opts.auth_opts).into())
                        .await?;

                let mut channel = session
                    .channel_open_session()
                    .err_into::<emf_ssh::Error>()
                    .await?;

                let x = channel.exec_cmd(&x.run).await?;

                if !x.success() {
                    let x: Result<Output, emf_ssh::Error> = x.into();

                    return x.map(drop).map_err(Error::SshError);
                }
            }
            host::Input::SetupPlanesSsh(host::SetupPlanesSsh {
                hosts,
                cp_addr,
                ssh_opts,
            }) => {
                let hosts = parse_hosts(&hosts)?;

                stream::iter(hosts)
                    .map(Ok)
                    .try_for_each_concurrent(10, |host| async move {
                        let mut session = emf_ssh::connect(
                            &host,
                            ssh_opts.port,
                            &ssh_opts.user,
                            (&ssh_opts.auth_opts).into(),
                        )
                        .await?;

                        let overrides = format!("CP_ADDR={}\nMGMT_ADDR={}", cp_addr, host);

                        session
                            .stream_file(overrides.as_bytes(), "/etc/emf/overrides.conf")
                            .await?;

                        Ok::<_, Error>(())
                    })
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
                )
                .await?;

                session.stream_file(contents.as_bytes(), path).await?;
            }
            host::Input::SyncFileSsh(host::SyncFileSsh {
                hosts,
                from,
                ssh_opts,
            }) => {
                let hosts = parse_hosts(&hosts)?;

                stream::iter(hosts)
                    .map(Ok)
                    .try_for_each_concurrent(10, |host| async move {
                        let mut session = emf_ssh::connect(
                            &host,
                            ssh_opts.port,
                            &ssh_opts.user,
                            (&ssh_opts.auth_opts).into(),
                        )
                        .await?;

                        session.push_file(&from, &from).await?;

                        Ok::<_, Error>(())
                    })
                    .await?;
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
