// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    api_utils::{create_command, get_hosts, wait_for_cmds_success, SendCmd, SendJob},
    display_utils::{display_cancelled, display_error, wrap_fut},
    error::EmfManagerCliError,
    parse_hosts,
};
use emf_wire_types::Host;
use std::collections::BTreeSet;
use structopt::StructOpt;

#[derive(StructOpt, Debug)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub struct UpdateRepoFileHosts {
    /// The hosts to update, e. g. mds[1,2].local
    #[structopt(required = true, min_values = 1)]
    hosts: Vec<String>,
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
    host_id: i32,
}

pub async fn update_repo_file_cli(config: UpdateRepoFileHosts) -> Result<(), EmfManagerCliError> {
    let r = parse_hosts(&config.hosts)?;

    tracing::debug!("Parsed hosts {:?}", r);

    let api_hosts = wrap_fut("Fetching hosts...", get_hosts()).await?;

    let xs = filter_known_hosts(&r, &api_hosts.objects);

    for x in r.iter() {
        if !has_host(&xs, &x) {
            display_cancelled(format!("Unknown host: {}", x));
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
        message: "Update Agent Repo files".into(),
    };

    let cmd = wrap_fut("Updating Repo files...", create_command(cmd)).await?;

    wait_for_cmds_success(&[cmd]).await?;

    Ok(())
}
