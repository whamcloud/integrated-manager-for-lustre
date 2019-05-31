// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::{
    env,
    net::{SocketAddr, ToSocketAddrs},
    path::PathBuf,
};

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

/// Get the `http_agent2` port from the env or panic
pub fn get_http_agent2_port() -> String {
    get_var("HTTP_AGENT2_PORT")
}

pub fn get_http_agent2_addr() -> SocketAddr {
    to_socket_addr(&get_server_host(), &get_http_agent2_port())
}

/// Get the server host from the env or panic
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

/// Get the path to the mailbox from the env or panic
pub fn get_mailbox_path() -> PathBuf {
    get_var("MAILBOX_PATH").into()
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
