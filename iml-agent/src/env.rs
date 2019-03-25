// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use lazy_static::lazy_static;
use std::{env, path::Path, process::Command};
use url::Url;

/// Checks if the given path exists in the FS
///
/// # Arguments
///
/// * `name` - The path to check
fn path_exists(name: &str) -> bool {
    Path::new(name).exists()
}

/// Gets the environment variable or panics
/// # Arguments
///
/// * `name` - Variable to read from the environment
pub fn get_var(name: &str) -> String {
    env::var(name).unwrap_or_else(|_| panic!("{} environment variable is required.", name))
}

/// Gets the manager url or panics
lazy_static! {
    pub static ref MANAGER_URL: Url =
        Url::parse(&get_var("IML_MANAGER_URL")).expect("Could not parse manager url");
}

fn get_private_pem_path() -> String {
    get_var("PRIVATE_PEM_PATH")
}

fn get_cert_path() -> String {
    get_var("CRT_PATH")
}

fn get_pfx_path() -> String {
    get_var("PFX_PATH")
}

/// Gets the pfx file.
/// If pfx is not found it will be created.
lazy_static! {
    pub static ref PFX: Vec<u8> = {
        let private_pem_path = get_private_pem_path();

        if !path_exists(&private_pem_path) {
            panic!("{} does not exist", private_pem_path)
        };

        let cert_path = get_cert_path();

        if !path_exists(&cert_path) {
            panic!("{} does not exist", cert_path)
        }

        let pfx_path = get_pfx_path();

        if !path_exists(&pfx_path) {
            Command::new("openssl")
                .args(&[
                    "pkcs12",
                    "-export",
                    "-out",
                    &pfx_path,
                    "-inkey",
                    &private_pem_path,
                    "-in",
                    &cert_path,
                    "-certfile",
                    "/etc/iml/authority.crt",
                    "-passout",
                    "pass:",
                ])
                .status()
                .expect("Error creating pfx");
        }

        std::fs::read(&pfx_path).expect("Could not read pfx")
    };
}
