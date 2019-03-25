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

static PRIVATE_PEM_PATH: &str = "/etc/iml/private.pem";
static CRT_PATH: &str = "/etc/iml/self.crt";
static PFX_PATH: &str = "/etc/iml/identity.pfx";

/// Gets the pfx file.
/// If pfx is not found it will be created.
lazy_static! {
    pub static ref PFX: Vec<u8> = {
        if !path_exists(PRIVATE_PEM_PATH) {
            panic!("{} does not exist", PRIVATE_PEM_PATH)
        };

        if !path_exists(CRT_PATH) {
            panic!("{} does not exist", CRT_PATH)
        }

        if !path_exists(PFX_PATH) {
            Command::new("openssl")
                .args(&[
                    "pkcs12",
                    "-export",
                    "-out",
                    PFX_PATH,
                    "-inkey",
                    PRIVATE_PEM_PATH,
                    "-in",
                    CRT_PATH,
                    "-certfile",
                    "/etc/iml/authority.crt",
                    "-passout",
                    "pass:",
                ])
                .status()
                .expect("Error creating pfx");
        }

        std::fs::read(PFX_PATH).expect("Could not read pfx")
    };
}
