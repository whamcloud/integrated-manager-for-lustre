// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{error::EmfApiError, graphql::Context};
use emf_lib_state_machine::input_document::{
    self,
    host::{
        add_emf_deb_repo_step, add_emf_rpm_repo_step, create_cli_conf, enable_emf_client_agent,
        enable_emf_server_agent, install_agent_client_rpms, install_agent_debs, install_agent_rpms,
        setup_planes, sync_dataplane_token, wait_for_host_availability,
    },
    Job,
};
use emf_wire_types::{
    host::Flavor,
    ssh::{AuthOpts, ProxyInput},
    CommandOrDryRun, DryRun, Host,
};
use futures::TryFutureExt;
use juniper::{FieldError, Value};
use std::collections::BTreeSet;

pub(crate) struct HostQuery;

#[juniper::graphql_object(Context = Context)]
impl HostQuery {
    /// List all known `Host` records.
    async fn list(context: &Context) -> juniper::FieldResult<Vec<Host>> {
        let xs = sqlx::query_as!(Host, "SELECT * FROM host")
            .fetch_all(&context.pg_pool)
            .err_into::<EmfApiError>()
            .await?;

        Ok(xs)
    }
}

pub(crate) struct HostMutation;

#[juniper::graphql_object(Context = Context)]
impl HostMutation {
    async fn deploy(
        context: &Context,
        hosts: Vec<String>,
        flavor: Flavor,
        dry_run: bool,
        ssh_port: Option<i32>,
        ssh_user: Option<String>,
        auth_opts: Option<AuthOpts>,
        proxy_opts: Option<ProxyInput>,
    ) -> juniper::FieldResult<CommandOrDryRun> {
        let xs = match parse_hosts(&hosts) {
            Ok(x) => x,
            Err(e) => {
                return Err(FieldError::new(
                    format!("Could not parse hosts: {}", e),
                    Value::null(),
                ))
            }
        };

        let proxy_opts = proxy_opts.map(|x| input_document::SshProxyOpts {
            host: x.host,
            port: x.port.map(|x| x as u16).unwrap_or(22),
            user: x.user.unwrap_or_else(|| "root".to_string()),
            password: x.password,
        });

        let opts = input_document::SshOpts {
            port: ssh_port.map(|x| x as u16).unwrap_or(22),
            user: ssh_user.unwrap_or_else(|| "root".to_string()),
            auth_opts: auth_opts.map(|x| x.into()).unwrap_or_default(),
            proxy_opts,
        };

        let doc = xs
            .into_iter()
            .fold(input_document::InputDocument::default(), |mut doc, host| {
                let steps = match flavor {
                    Flavor::Server => vec![
                        setup_planes(host.clone(), opts.clone()),
                        sync_dataplane_token(host.clone(), opts.clone()),
                        add_emf_rpm_repo_step(host.clone(), opts.clone()),
                        create_cli_conf(host.clone(), opts.clone()),
                        install_agent_rpms(host.clone(), opts.clone()),
                        enable_emf_server_agent(host.clone(), opts.clone()),
                        wait_for_host_availability(host.clone()),
                    ],
                    Flavor::UbuntuDgx => vec![
                        setup_planes(host.clone(), opts.clone()),
                        sync_dataplane_token(host.clone(), opts.clone()),
                        add_emf_deb_repo_step(host.clone(), opts.clone()),
                        install_agent_debs(host.clone(), opts.clone()),
                        enable_emf_client_agent(host.clone(), opts.clone()),
                        wait_for_host_availability(host.clone()),
                    ],
                    Flavor::Client => vec![
                        setup_planes(host.clone(), opts.clone()),
                        sync_dataplane_token(host.clone(), opts.clone()),
                        add_emf_rpm_repo_step(host.clone(), opts.clone()),
                        create_cli_conf(host.clone(), opts.clone()),
                        install_agent_client_rpms(host.clone(), opts.clone()),
                        enable_emf_client_agent(host.clone(), opts.clone()),
                        wait_for_host_availability(host.clone()),
                    ],
                };

                doc.jobs.insert(
                    format!("deploy_{}", &host),
                    Job {
                        name: format!("Deploy node {}", &host),
                        needs: BTreeSet::new(),
                        steps,
                    },
                );

                doc
            });

        let yaml = serde_yaml::to_string(&doc)?;

        if dry_run {
            return Ok(CommandOrDryRun::DryRun(DryRun { yaml }));
        }

        let port = emf_manager_env::get_port("API_SERVICE_STATE_MACHINE_SERVICE_PORT");

        let resp = context
            .http_client
            .post(&format!("http://localhost:{}/submit", port))
            .body(serde_yaml::to_string(&doc)?)
            .send()
            .await?;

        let status = resp.status();

        if status.is_client_error() || status.is_server_error() {
            let err_text = resp.text().await?;

            return Err(FieldError::new(err_text, Value::null()));
        }

        let cmd = resp.json().await?;

        Ok(CommandOrDryRun::Command(cmd))
    }
}

pub fn parse_hosts(hosts: &[String]) -> Result<BTreeSet<String>, String> {
    let parsed: Vec<BTreeSet<String>> = hosts
        .iter()
        .map(|x| hostlist_parser::parse(x))
        .collect::<Result<_, _>>()
        .map_err(|e| format!("{}", e))?;

    let union = parsed
        .into_iter()
        .fold(BTreeSet::new(), |acc, h| acc.union(&h).cloned().collect());

    Ok(union)
}
