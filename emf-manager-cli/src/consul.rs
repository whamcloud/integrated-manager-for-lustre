// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    display_utils::{display_success, wrap_fut},
    error::EmfManagerCliError,
    parse_hosts,
    ssh::SshOpts,
};
use emf_cmd::CheckedCommandExt;
use emf_fs::create_tmp_dir;
use emf_ssh::SshHandleExt;
use futures::{stream, StreamExt, TryStreamExt};
use std::{collections::BTreeSet, io, iter::FromIterator, path::Path, process::Stdio};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
struct Config {
    /// The datacenter name to bootstrap
    dc: String,
    /// The address to bind consul to. This can be set to a [go-sockaddr](https://godoc.org/github.com/hashicorp/go-sockaddr/template) template
    bind_addr: String,
    /// A hostlist expression of servers to bootstrap. Supports multiple hostlists.
    #[structopt(required = true, long)]
    consul_servers: Vec<String>,
    /// A hostlist expression of clients to bootstrap. Supports multiple hostlists.
    #[structopt(required = true, long)]
    consul_clients: Vec<String>,
    /// 32 byte Base64 encoded key used for gossip encryption.
    /// If no key is provided `consul keygen` will be called on the local node to generate one.
    #[structopt(long)]
    consul_gossip_key: Option<String>,
}

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub struct Bootstrap {
    #[structopt(flatten)]
    config: Config,
    #[structopt(flatten)]
    ssh_opts: SshOpts,
}

#[derive(Debug, StructOpt)]
#[structopt(setting = structopt::clap::AppSettings::ColoredHelp)]
pub enum Command {
    /// Bootstrap a consul datacenter.
    /// This will generate a CA, agent keys, gossip keys, and `consul.json`.
    ///
    /// Keys and config files will be distributed via SSH to specified servers and clients.
    Bootstrap(Bootstrap),
}

#[derive(Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Conf {
    pub ca_file: String,
    pub cert_file: String,
    pub data_dir: String,
    pub datacenter: String,
    pub bootstrap_expect: i64,
    pub encrypt: String,
    pub key_file: String,
    pub verify_incoming: bool,
    pub verify_outgoing: bool,
    pub verify_server_hostname: bool,
    pub enable_local_script_checks: bool,
    pub retry_join: Vec<String>,
    pub ports: PortConf,
    pub bind_addr: String,
    pub server: bool,
    pub connect: ConnectConf,
}

#[derive(Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct PortConf {
    grpc: u16,
}

#[derive(Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ConnectConf {
    pub enabled: bool,
}

pub async fn cli(command: Command) -> Result<(), EmfManagerCliError> {
    match command {
        Command::Bootstrap(Bootstrap { config, ssh_opts }) => {
            consul_exists().await?;

            let gossip_encrypt_key = match config.consul_gossip_key.as_ref() {
                Some(k) => k.to_string(),
                None => create_gossip_key().await?,
            };

            let tmp_dir = create_tmp_dir("emf-consul-bootstrap".to_string()).await?;

            create_ca(&tmp_dir).await?;

            let servers = parse_hosts(&config.consul_servers)?;
            let server_nodes = Vec::from_iter(servers.clone());

            wrap_fut(
                "Bootstraping Servers",
                setup_nodes(
                    &config,
                    &ssh_opts,
                    servers,
                    server_nodes.clone(),
                    &tmp_dir,
                    &gossip_encrypt_key,
                    true,
                ),
            )
            .await?;

            display_success(format!(
                "Bootstrapped the following servers: {:?}",
                server_nodes
            ));

            let clients = parse_hosts(&config.consul_clients)?;

            let msg = format!(
                "Bootstrapped the following clients: {:?}",
                clients.iter().collect::<Vec<_>>()
            );

            wrap_fut(
                "Bootstrapping Clients",
                setup_nodes(
                    &config,
                    &ssh_opts,
                    clients,
                    server_nodes,
                    &tmp_dir,
                    &gossip_encrypt_key,
                    false,
                ),
            )
            .await?;

            display_success(msg);
        }
    };

    Ok(())
}

async fn setup_nodes(
    config: &Config,
    ssh_opts: &SshOpts,
    xs: BTreeSet<String>,
    server_nodes: Vec<String>,
    tmp_dir: &Path,
    gossip_encrypt_key: &str,
    is_servers: bool,
) -> Result<(), EmfManagerCliError> {
    for _ in xs.iter() {
        create_agent_cert(tmp_dir, &config.dc, is_servers).await?;
    }

    stream::iter(xs)
        .enumerate()
        .map(Ok::<_, EmfManagerCliError>)
        .and_then(|(idx, host)| {
            let auth = emf_ssh::Auth::from(&ssh_opts.auth_opts);
            let fut = emf_ssh::connect(host, ssh_opts.port, &ssh_opts.user, auth);

            async move {
                let session = fut.await?;

                Ok((idx, session))
            }
        })
        .err_into()
        .try_for_each_concurrent(5, |(idx, session)| {
            deploy_consul(
                config,
                tmp_dir,
                session,
                server_nodes.clone(),
                gossip_encrypt_key,
                idx,
                is_servers,
            )
        })
        .await?;

    Ok(())
}

async fn consul_exists() -> Result<(), EmfManagerCliError> {
    match emf_cmd::Command::new("consul")
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .status()
        .await
    {
        Err(err) if err.kind() == io::ErrorKind::NotFound => {
            Err(EmfManagerCliError::DoesNotExist("Local consul binary"))
        }
        _ => Ok(()),
    }
}

async fn deploy_consul(
    config: &Config,
    tmp_dir: &Path,
    mut session: emf_ssh::Handle,
    servers: Vec<String>,
    gossip_encrypt_key: &str,
    idx: usize,
    is_server: bool,
) -> Result<(), EmfManagerCliError> {
    let server_or_client = if is_server { "server" } else { "client" };

    let ca_file = "consul-agent-ca.pem";
    let cert_file = format!("{}-{}-consul-{}.pem", config.dc, server_or_client, idx);
    let key_file = format!("{}-{}-consul-{}-key.pem", config.dc, server_or_client, idx);

    let conf_path = Path::new("/etc/emf");

    let conf = Conf {
        ca_file: conf_path
            .join("consul-agent-ca.pem")
            .to_string_lossy()
            .to_string(),
        cert_file: conf_path.join(&cert_file).to_string_lossy().to_string(),
        data_dir: "/opt/consul".to_string(),
        datacenter: config.dc.to_string(),
        bootstrap_expect: if is_server { servers.len() as i64 } else { 0 },
        encrypt: gossip_encrypt_key.to_string(),
        key_file: conf_path.join(&key_file).to_string_lossy().to_string(),
        verify_incoming: true,
        verify_outgoing: true,
        verify_server_hostname: true,
        enable_local_script_checks: true,
        retry_join: servers,
        ports: PortConf { grpc: 8502 },
        bind_addr: config.bind_addr.to_string(),
        server: is_server,
        connect: ConnectConf { enabled: is_server },
    };

    session
        .push_file(tmp_dir.join(&ca_file), conf_path.join(&ca_file))
        .await?;

    session
        .push_file(tmp_dir.join(&cert_file), conf_path.join(&cert_file))
        .await?;

    session
        .push_file(tmp_dir.join(&key_file), conf_path.join(&key_file))
        .await?;

    session
        .stream_file(
            serde_json::to_string_pretty(&conf)?.as_bytes(),
            "/etc/consul.d/consul.json",
        )
        .await?;

    Ok(())
}

async fn create_gossip_key() -> Result<String, EmfManagerCliError> {
    let o = emf_cmd::Command::new("consul")
        .arg("keygen")
        .checked_output()
        .await?;

    let x = String::from_utf8(o.stdout)?.trim().to_string();

    Ok(x)
}

async fn create_ca(dir: &Path) -> Result<(), EmfManagerCliError> {
    let _ = emf_cmd::Command::new("consul")
        .args(vec!["tls", "ca", "create"])
        .current_dir(dir)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .checked_status()
        .await?;

    Ok(())
}

async fn create_agent_cert(
    dir: &Path,
    dc: &str,
    is_server: bool,
) -> Result<(), EmfManagerCliError> {
    emf_cmd::Command::new("consul")
        .args(vec!["tls", "cert", "create", "-dc", dc])
        .current_dir(dir)
        .arg(if is_server { "-server" } else { "-client" })
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .checked_status()
        .await?;

    Ok(())
}
