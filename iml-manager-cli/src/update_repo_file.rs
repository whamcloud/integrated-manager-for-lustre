// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{create_command, get_hosts, wait_for_cmds, SendCmd, SendJob},
    display_utils::{display_cancelled, display_error, wrap_fut},
    error::ImlManagerCliError,
};
use iml_wire_types::Host;
use std::collections::BTreeSet;
use structopt::StructOpt;

#[derive(StructOpt, Debug)]
pub struct UpdateRepoFileHosts {
    /// The host(s) to update. Takes a hostlist expression
    #[structopt(short = "h", long = "hosts")]
    hosts: String,
}

fn filter_known_hosts<'a, 'b>(
    hostlist: &'b BTreeSet<String>,
    api_hosts: &'a [Host],
) -> Vec<&'a Host> {
    api_hosts
        .iter()
        .filter(move |x| hostlist.contains(&x.fqdn) || hostlist.contains(&x.nodename))
        .collect()
}

fn has_host(api_hosts: &[&Host], host: &str) -> bool {
    api_hosts
        .iter()
        .any(|y| y.fqdn == host || y.nodename == host)
}

#[derive(serde::Serialize)]
pub struct HostId {
    host_id: u32,
}

pub async fn update_repo_file_cli(config: UpdateRepoFileHosts) -> Result<(), ImlManagerCliError> {
    let r = hostlist_parser::parse(&config.hosts)?;

    tracing::debug!("Parsed hosts {:?}", r);

    let api_hosts = wrap_fut("Fetching hosts...", get_hosts()).await?;

    let xs = filter_known_hosts(&r, &api_hosts.objects);

    for x in r.iter() {
        if !has_host(&xs, &x) {
            display_cancelled(format!("Host {} unknown to IML.", x));
        }
    }

    if xs.is_empty() {
        display_error("0 hosts can be updated. Exiting");

        return Ok(());
    }

    let cmd = SendCmd {
        jobs: xs
            .iter()
            .map(|x| SendJob {
                class_name: "UpdateYumFileJob".into(),
                args: HostId { host_id: x.id },
            })
            .collect(),
        message: "Update IML Agent Repo files".into(),
    };

    let cmd = wrap_fut("Updating Repo files...", create_command(cmd)).await?;

    wait_for_cmds(vec![cmd]).await?;

    Ok(())
}
