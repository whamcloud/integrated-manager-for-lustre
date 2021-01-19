// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use lazy_static::lazy_static;
use std::{env, fs::File, io::Read};
use url::Url;

/// Gets the environment variable or panics
/// # Arguments
///
/// * `name` - Variable to read from the environment
pub fn get_var(name: &str) -> String {
    env::var(name).unwrap_or_else(|_| panic!("{} environment variable is required.", name))
}

pub fn get_var_else(name: &str, default: &str) -> String {
    env::var(name).unwrap_or_else(|_| default.to_string())
}

lazy_static! {
    // Gets the manager url or panics
    pub static ref MANAGER_URL: Url =
        Url::parse(&get_var("EMF_MANAGER_URL")).expect("Could not parse manager url");
}

fn get_private_pem_path() -> String {
    get_var("PRIVATE_PEM_PATH")
}

fn get_cert_path() -> String {
    get_var("CRT_PATH")
}

pub fn sock_dir() -> String {
    get_var("SOCK_DIR")
}

pub fn get_ldev_conf() -> String {
    get_var("LDEV_CONF_PATH")
}

pub fn get_journal_port() -> u32 {
    get_var_else("JOURNAL_PORT", "19531")
        .parse::<u32>()
        .expect("Could not parse JOURNAL_PORT")
}

/// Return socket address for a given mailbox
pub fn mailbox_sock(mailbox: &str) -> String {
    format!("{}/postman-{}.sock", sock_dir(), mailbox)
}

pub fn get_openmpi_path() -> String {
    get_var("OPENMPI_PATH")
}

pub fn get_openmpi_count() -> u32 {
    get_var_else("OPENMPI_COUNT", "4")
        .parse::<u32>()
        .expect("Could not parse OPENMPI_COUNT")
}

lazy_static! {
    pub static ref PEM: Vec<u8> = {
        let mut result = Vec::new();

        let private_pem_path = get_private_pem_path();

        let mut private_pem = File::open(private_pem_path)
            .unwrap_or_else(|e| panic!("Error opening {}: {}", get_private_pem_path(), e));
        private_pem
            .read_to_end(&mut result)
            .expect("Couldn't read PEM");

        let cert_path = get_cert_path();

        let mut cert = File::open(cert_path)
            .unwrap_or_else(|e| panic!("Error opening {}: {}", get_cert_path(), e));
        cert.read_to_end(&mut result)
            .expect("Couldn't read the certificate");

        result
    };
}
