// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use lazy_static::lazy_static;
use std::{
    collections::{BTreeMap, HashMap},
    env,
    net::{SocketAddr, ToSocketAddrs},
    path::PathBuf,
};
use url::Url;

lazy_static! {
    static ref RUNNING_IN_DOCKER: bool = std::fs::metadata("/.dockerenv").is_ok();
}

lazy_static! {
    pub static ref ACTION_RUNNER_URL: Url = get_action_runner_url();
}

/// Get the environment variable or panic
fn get_var(name: &str) -> String {
    env::var(name).unwrap_or_else(|_| panic!("{} environment variable is required.", name))
}

/// Convert a given host and port to a `SocketAddr` or panic
fn to_socket_addr(host: &str, port: &str) -> SocketAddr {
    let raw_addr = format!("{}:{}", host, port);

    let mut addrs_iter = raw_addr.to_socket_addrs().unwrap_or_else(|_| {
        panic!(
            "Address not parsable to SocketAddr. host: {}, port: {}",
            host, port
        )
    });

    addrs_iter
        .next()
        .expect("Could not convert to a SocketAddr")
}

fn empty_str_to_none(x: String) -> Option<String> {
    match x.as_ref() {
        "" => None,
        _ => Some(x),
    }
}

fn string_to_bool(x: String) -> bool {
    match x.trim().to_lowercase().as_ref() {
        "true" => true,
        _ => false,
    }
}

pub fn get_log_path() -> PathBuf {
    get_var("LOG_PATH").into()
}

pub fn get_dblog_hw() -> u32 {
    get_var("DBLOG_HW").parse().unwrap()
}

pub fn get_dblog_lw() -> u32 {
    get_var("DBLOG_LW").parse().unwrap()
}

/// Determine if local node is a docker volume
pub fn running_in_docker() -> bool {
    *RUNNING_IN_DOCKER
}

/// Get anonymous read permission from the env or panic
pub fn get_allow_anonymous_read() -> bool {
    string_to_bool(get_var("ALLOW_ANONYMOUS_READ"))
}

/// Get build num from the env or panic
pub fn get_build() -> String {
    get_var("BUILD")
}

/// Get is release from the env or panic
pub fn get_is_release() -> bool {
    string_to_bool(get_var("IS_RELEASE"))
}

/// Get version from the env or panic
pub fn get_version() -> String {
    get_var("VERSION")
}

/// Get exascaler version
pub fn get_exa_version() -> Option<String> {
    env::var("EXA_VERSION").ok()
}

/// Get the broker URL from the env or panic
pub fn get_amqp_broker_url() -> String {
    get_var("AMQP_BROKER_URL")
}

/// Get the broker user from the env or panic
pub fn get_user() -> String {
    get_var("AMQP_BROKER_USER")
}

/// Get the broker password from the env or panic
pub fn get_password() -> String {
    get_var("AMQP_BROKER_PASSWORD")
}

/// Get the broker vhost from the env or panic
pub fn get_vhost() -> String {
    get_var("AMQP_BROKER_VHOST")
}

/// Get the broker host from the env or panic
pub fn get_host() -> String {
    get_var("AMQP_BROKER_HOST")
}

/// Get the broker port from the env or panic
pub fn get_port() -> String {
    get_var("AMQP_BROKER_PORT")
}

/// Get the IML API port from the env or panic
pub fn get_iml_api_port() -> String {
    get_var("IML_API_PORT")
}

/// Get the IML API address from the env or panic
pub fn get_iml_api_addr() -> SocketAddr {
    to_socket_addr(&get_server_host(), &get_iml_api_port())
}

pub fn get_iml_api_bind_addr() -> SocketAddr {
    to_socket_addr(&get_service_host(), &get_iml_api_port())
}

/// Get the `http_agent2` port from the env or panic
pub fn get_http_agent2_port() -> String {
    get_var("HTTP_AGENT2_PORT")
}

pub fn get_http_agent2_addr() -> SocketAddr {
    to_socket_addr(&get_server_host(), &get_http_agent2_port())
}

/// Get the name of the host a service should bind to
pub fn get_service_host() -> String {
    env::var("SERVICE_HOST").unwrap_or_else(|_| "127.0.0.1".to_string())
}

/// Get the nginx host from the env or panic
pub fn get_server_host() -> String {
    get_var("PROXY_HOST")
}

/// Get the AMQP server address or panic
pub fn get_addr() -> SocketAddr {
    to_socket_addr(&get_host(), &get_port())
}

/// Get the warp drive port from the env or panic
pub fn get_warp_drive_port() -> String {
    get_var("WARP_DRIVE_PORT")
}

/// Get the warp drive address from the env or panic
pub fn get_warp_drive_addr() -> SocketAddr {
    to_socket_addr(&get_server_host(), &get_warp_drive_port())
}

/// Get the mailbox port from the env or panic
pub fn get_mailbox_port() -> String {
    get_var("MAILBOX_PORT")
}
/// Get the mailbox address from the env or panic
pub fn get_mailbox_addr() -> SocketAddr {
    to_socket_addr(&get_server_host(), &get_mailbox_port())
}

/// Get the timer port
pub fn get_timer_port() -> String {
    get_var("TIMER_PORT")
}

pub fn get_timer_fqdn() -> String {
    get_var("TIMER_SERVER_FQDN")
}

/// Get the timer address from the env or panic
pub fn get_timer_addr() -> SocketAddr {
    to_socket_addr(&get_timer_fqdn(), &get_timer_port())
}

/// Get the influxdb port from the env or panic
pub fn get_influxdb_port() -> String {
    get_var("INFLUXDB_PORT")
}

pub fn get_influxdb_server_fqdn() -> String {
    get_var("INFLUXDB_SERVER_FQDN")
}

/// Get the influxdb address from the env or panic
pub fn get_influxdb_addr() -> SocketAddr {
    to_socket_addr(&get_influxdb_server_fqdn(), &get_influxdb_port())
}

/// Get the metrics influxdb database name
pub fn get_influxdb_metrics_db() -> String {
    get_var("INFLUXDB_IML_STATS_DB")
}

/// Get the devices port or panic
pub fn get_device_aggregator_port() -> String {
    get_var("DEVICE_AGGREGATOR_PORT")
}

pub fn get_device_aggregator_addr() -> SocketAddr {
    to_socket_addr(&get_server_host(), &get_device_aggregator_port())
}

/// Get the api key from the env or panic
pub fn get_api_key() -> String {
    get_var("API_KEY")
}

/// Get the api user from the env or panic
pub fn get_api_user() -> String {
    get_var("API_USER")
}

pub fn get_manager_url() -> String {
    get_var("SERVER_HTTP_URL")
}

pub fn get_db_user() -> String {
    get_var("DB_USER")
}

pub fn get_db_host() -> Option<String> {
    empty_str_to_none(get_var("DB_HOST"))
}

pub fn get_db_port() -> Option<u16> {
    env::var("DB_PORT").ok().map(|l| l.parse().ok()).flatten()
}

pub fn get_db_name() -> Option<String> {
    empty_str_to_none(get_var("DB_NAME"))
}

pub fn get_db_password() -> Option<String> {
    empty_str_to_none(get_var("DB_PASSWORD"))
}

pub fn get_pool_limit() -> Option<u32> {
    env::var("POOL_LIMIT")
        .ok()
        .map(|l| l.parse().ok())
        .flatten()
}

/// Get the report port from the env or panic
pub fn get_report_port() -> String {
    get_var("REPORT_PORT")
}
/// Get the report address from the env or panic
pub fn get_report_addr() -> SocketAddr {
    to_socket_addr(&get_server_host(), &get_report_port())
}

/// Get the path to the report from the env or panic
pub fn get_report_path() -> PathBuf {
    get_var("REPORT_PATH").into()
}

pub fn get_branding() -> String {
    get_var("BRANDING")
}

pub fn get_use_stratagem() -> bool {
    string_to_bool(get_var("USE_STRATAGEM"))
}

pub fn get_use_snapshots() -> bool {
    string_to_bool(env::var("USE_SNAPSHOTS").unwrap_or_else(|_| "false".to_string()))
}

pub fn get_action_runner_host() -> String {
    get_var("ACTION_RUNNER_HOST")
}

pub fn get_action_runner_port() -> String {
    get_var("ACTION_RUNNER_PORT")
}

pub fn get_action_runner_url() -> Url {
    Url::parse(&format!(
        "http://{}:{}",
        get_action_runner_host(),
        get_action_runner_port()
    ))
    .expect("Could not parse action runner Url")
}

pub fn get_action_runner_uds() -> String {
    "/var/run/iml-action-runner.sock".to_string()
}

/// Get the nginx proxy port or panic
pub fn get_proxy_port() -> String {
    get_var("HTTPS_FRONTEND_PORT")
}

/// Get the proxy URL or panic
pub fn get_proxy_url() -> Url {
    let x = format!("https://{}:{}/", get_server_host(), get_proxy_port());

    Url::parse(&x).expect("Could not parse proxy URL")
}

pub fn get_sfa_endpoints() -> Option<Vec<Vec<Url>>> {
    let xs: BTreeMap<_, _> = env::vars()
        .filter(|(k, _)| k.starts_with("SFA_ENDPOINTS_"))
        .collect();

    let xs = xs.values().fold(vec![], |mut acc, x| {
        let xs: Vec<_> = x
            .split('|')
            .filter(|x| !x.is_empty())
            .map(|x| Url::parse(x).expect("Could not parse URL entry"))
            .collect();

        if !xs.is_empty() {
            acc.push(xs);
        }

        acc
    });

    if xs.is_empty() {
        None
    } else {
        Some(xs)
    }
}

/// Gets a hash of db connection values
pub fn get_db_conn_hash() -> HashMap<String, String> {
    let mut xs = HashMap::new();

    xs.insert("user".to_string(), get_db_user());

    let host = match get_db_host() {
        Some(x) => x,
        None => "/var/run/postgresql".into(),
    };

    xs.insert("host".to_string(), host);

    if let Some(x) = get_db_name() {
        xs.insert("dbname".to_string(), x);
    }

    if let Some(x) = get_db_password() {
        xs.insert("password".to_string(), x);
    }

    // Convert executable name to application_name for Postgres
    if let Some(x) = std::env::current_exe()
        .unwrap_or_else(|_| "".into())
        .file_name()
    {
        xs.insert(
            "application_name".to_string(),
            x.to_string_lossy().to_string(),
        );
    }

    xs
}

/// Gets a connection string from the IML env
pub fn get_db_conn_string() -> String {
    let xs = get_db_conn_hash();
    xs.iter()
        .map(|(k, v)| format!("{}={}", k, v))
        .collect::<Vec<String>>()
        .join(" ")
}
